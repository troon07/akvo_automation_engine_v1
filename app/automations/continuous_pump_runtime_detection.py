import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from app.config.automation_settings import (
    CONTINUOUS_PUMP_RUNTIME_DETECTION,
    OFFLINE_DETECTION,
)
from app.config.validation_settings import VALIDATION_SETTINGS
from app.database.queries import (
    create_alert,
    get_pump_runtime_sensor_data_since,
    has_unresolved_alert,
    resolve_alert,
)
from app.services.automation_execution_logger import log_automation_execution

logger = logging.getLogger(__name__)


def _parse_esp_log_at(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, str):
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            logger.warning(
                "event=invalid_sensor_timestamp esp_log_at=%s status=skipped",
                value,
            )
            return None
    else:
        logger.warning(
            "event=unsupported_sensor_timestamp esp_log_at=%r status=skipped",
            value,
        )
        return None

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)


def _is_on(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return bool(value)

    if isinstance(value, str):
        return value.strip().lower() in {"on", "true", "1", "running", "enabled"}

    return False


def _resolve_pump_runtime_alert_if_needed(machine_id: str) -> int:
    if not has_unresolved_alert(
        machine_id=machine_id,
        alert_type=CONTINUOUS_PUMP_RUNTIME_DETECTION.alert_type,
    ):
        return 0

    resolve_alert(
        machine_id=machine_id,
        alert_type=CONTINUOUS_PUMP_RUNTIME_DETECTION.alert_type,
    )

    if has_unresolved_alert(
        machine_id=machine_id,
        alert_type=CONTINUOUS_PUMP_RUNTIME_DETECTION.alert_type,
    ):
        logger.debug(
            "event=continuous_pump_runtime_resolution_pending machine_id=%s alert_type=%s status=pending",
            machine_id,
            CONTINUOUS_PUMP_RUNTIME_DETECTION.alert_type,
        )
        return 0

    logger.info(
        "event=continuous_pump_runtime_resolved machine_id=%s alert_type=%s status=resolved",
        machine_id,
        CONTINUOUS_PUMP_RUNTIME_DETECTION.alert_type,
    )
    return 1


def _analyze_machine_rows(
    machine_id: str,
    rows: list[dict[str, Any]],
    now: datetime,
) -> tuple[int, int, int]:
    """Analyze one machine's bounded recent telemetry for pump runtime."""

    latest_row = rows[-1]
    latest_timestamp = latest_row["parsed_esp_log_at"]
    sample_count = len(rows)

    telemetry_is_fresh = now - latest_timestamp <= OFFLINE_DETECTION.offline_threshold
    machine_operational = _is_on(latest_row.get("compressor_status")) or _is_on(
        latest_row.get("fan_status")
    )

    if (
        not telemetry_is_fresh
        or not machine_operational
        or sample_count < VALIDATION_SETTINGS.minimum_continuous_pump_samples
    ):
        return 0, 0, _resolve_pump_runtime_alert_if_needed(machine_id)

    pump_continuously_on = all(_is_on(row.get("pump_status")) for row in rows)
    tank_never_full = all(not _is_on(row.get("int_tank_full")) for row in rows)
    continuous_runtime_detected = pump_continuously_on and tank_never_full

    if not continuous_runtime_detected:
        return 0, 0, _resolve_pump_runtime_alert_if_needed(machine_id)

    if has_unresolved_alert(
        machine_id=machine_id,
        alert_type=CONTINUOUS_PUMP_RUNTIME_DETECTION.alert_type,
    ):
        return 1, 0, 0

    logger.warning(
        "event=continuous_pump_runtime_detected machine_id=%s alert_type=%s sample_count=%s window_minutes=%s status=alerting",
        machine_id,
        CONTINUOUS_PUMP_RUNTIME_DETECTION.alert_type,
        sample_count,
        VALIDATION_SETTINGS.continuous_pump_runtime_window_minutes,
    )
    created_alert = create_alert(
        machine_id=machine_id,
        alert_type=CONTINUOUS_PUMP_RUNTIME_DETECTION.alert_type,
        severity=CONTINUOUS_PUMP_RUNTIME_DETECTION.severity,
        message="Pump remained continuously ON while the internal tank was not full.",
        metadata={
            "telemetry_sample_count": sample_count,
            "analysis_window_minutes": (
                VALIDATION_SETTINGS.continuous_pump_runtime_window_minutes
            ),
            "pump_runtime_continuity_confirmed": True,
        },
    )
    return 1, 1 if created_alert else 0, 0


def run_continuous_pump_runtime_detection() -> bool:
    """Detect conservative V1 continuous pump runtime behavior."""

    started_at = datetime.now(UTC)
    analyzed_machine_count = 0
    detections = 0

    try:
        now = datetime.now(UTC)
        since = now - timedelta(
            minutes=VALIDATION_SETTINGS.continuous_pump_runtime_window_minutes
        )
        sensor_rows = get_pump_runtime_sensor_data_since(since)
        rows_by_machine: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for row in sensor_rows:
            machine_id = row.get("machine_id")
            if not machine_id:
                logger.warning(
                    "event=continuous_pump_runtime_row_missing_machine_id row=%s status=skipped",
                    row,
                )
                continue

            parsed_timestamp = _parse_esp_log_at(row.get("esp_log_at"))
            if parsed_timestamp is None:
                logger.warning(
                    "event=continuous_pump_runtime_row_skipped reason=invalid_timestamp row=%s status=skipped",
                    row,
                )
                continue

            normalized_row = dict(row)
            normalized_row["parsed_esp_log_at"] = parsed_timestamp
            rows_by_machine[str(machine_id)].append(normalized_row)

        alerts_created = 0
        alerts_resolved = 0

        for machine_id, machine_rows in rows_by_machine.items():
            analyzed_machine_count += 1
            machine_rows.sort(key=lambda item: item["parsed_esp_log_at"])
            detected, created, resolved = _analyze_machine_rows(
                machine_id=machine_id,
                rows=machine_rows,
                now=now,
            )
            detections += detected
            alerts_created += created
            alerts_resolved += resolved

        completed_at = datetime.now(UTC)
        log_automation_execution(
            automation_name=CONTINUOUS_PUMP_RUNTIME_DETECTION.automation_id,
            started_at=started_at,
            completed_at=completed_at,
            execution_duration_ms=round(
                (completed_at - started_at).total_seconds() * 1000,
                2,
            ),
            analyzed_machine_count=analyzed_machine_count,
            detection_count=detections,
            status="success",
        )
        logger.info(
            "event=continuous_pump_runtime_detection_finished automation_id=%s analyzed_machines=%s detections=%s alerts_created=%s alerts_resolved=%s status=success",
            CONTINUOUS_PUMP_RUNTIME_DETECTION.automation_id,
            analyzed_machine_count,
            detections,
            alerts_created,
            alerts_resolved,
        )
        return True
    except Exception as exc:
        completed_at = datetime.now(UTC)
        log_automation_execution(
            automation_name=CONTINUOUS_PUMP_RUNTIME_DETECTION.automation_id,
            started_at=started_at,
            completed_at=completed_at,
            execution_duration_ms=round(
                (completed_at - started_at).total_seconds() * 1000,
                2,
            ),
            analyzed_machine_count=analyzed_machine_count,
            detection_count=detections,
            status="failed",
            error_message=str(exc),
        )
        logger.exception(
            "event=automation_failed automation_id=%s status=failed",
            CONTINUOUS_PUMP_RUNTIME_DETECTION.automation_id,
        )
        return False
