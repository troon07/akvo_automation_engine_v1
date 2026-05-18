import logging
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from app.config.automation_settings import FAN_COMPRESSOR_SEQUENCE
from app.database.queries import (
    create_alert,
    get_fan_compressor_sensor_data_since,
    has_unresolved_alert,
    resolve_alert,
)

logger = logging.getLogger(__name__)


def _parse_esp_log_at(value: Any) -> datetime | None:
    """Parse a Supabase timestamp value into a timezone-aware UTC datetime."""

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


def _is_on(value: Any) -> bool | None:
    """Normalize a sensor status into an ON/OFF boolean."""

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return bool(value)

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"on", "true", "1", "running", "enabled"}:
            return True
        if normalized in {"off", "false", "0", "stopped", "disabled"}:
            return False

    return None


def _resolve_if_unresolved(machine_id: str, alert_type: str, log_message: str) -> None:
    """Resolve an alert only when an unresolved alert exists."""

    if not has_unresolved_alert(machine_id=machine_id, alert_type=alert_type):
        return

    resolved_alert = resolve_alert(machine_id=machine_id, alert_type=alert_type)
    if resolved_alert:
        logger.info(log_message, machine_id, alert_type)


def _fan_was_continuously_on(
    rows: list[dict[str, Any]],
    start_time: datetime,
    end_time: datetime,
) -> bool:
    """Return whether fan readings in a time window were continuously ON."""

    window_rows = [
        row
        for row in rows
        if start_time <= row["parsed_esp_log_at"] <= end_time
    ]
    if not window_rows:
        return False

    return all(_is_on(row.get("fan_status")) is True for row in window_rows)


def _has_runtime_mismatch(latest_row: dict[str, Any]) -> bool:
    """Return whether the latest row shows compressor ON while fan is not ON."""

    compressor_on = _is_on(latest_row.get("compressor_status"))
    fan_on = _is_on(latest_row.get("fan_status"))
    return compressor_on is True and fan_on is not True


def _validate_machine_sequence(
    machine_id: str,
    rows: list[dict[str, Any]],
    now: datetime,
) -> None:
    """Validate fan/compressor sequencing rules for one machine."""

    startup_violation = False
    shutdown_violation = False
    shutdown_pending = False
    latest_row = rows[-1]
    earliest_row_time = rows[0]["parsed_esp_log_at"]

    previous_compressor_on: bool | None = None
    for index, row in enumerate(rows):
        current_compressor_on = _is_on(row.get("compressor_status"))
        if current_compressor_on is None:
            continue

        event_time = row["parsed_esp_log_at"]

        if previous_compressor_on is False and current_compressor_on is True:
            if (
                event_time - FAN_COMPRESSOR_SEQUENCE.startup_fan_lead_time
                < earliest_row_time
            ):
                logger.debug(
                    "event=startup_sequence_validation_skipped machine_id=%s alert_type=%s reason=insufficient_history status=skipped",
                    machine_id,
                    FAN_COMPRESSOR_SEQUENCE.startup_alert_type,
                )
                previous_compressor_on = current_compressor_on
                continue

            fan_ready = _fan_was_continuously_on(
                rows=rows,
                start_time=event_time
                - FAN_COMPRESSOR_SEQUENCE.startup_fan_lead_time,
                end_time=event_time,
            )
            if not fan_ready:
                startup_violation = True
                logger.warning(
                    "event=improper_startup_sequence_detected machine_id=%s alert_type=%s status=alerting",
                    machine_id,
                    FAN_COMPRESSOR_SEQUENCE.startup_alert_type,
                )

        if previous_compressor_on is True and current_compressor_on is False:
            validation_end = min(
                event_time + FAN_COMPRESSOR_SEQUENCE.shutdown_fan_run_time,
                now,
            )
            shutdown_complete = (
                event_time + FAN_COMPRESSOR_SEQUENCE.shutdown_fan_run_time <= now
            )
            shutdown_window = [
                item
                for item in rows[index:]
                if event_time <= item["parsed_esp_log_at"] <= validation_end
            ]
            fan_is_off_in_window = any(
                _is_on(item.get("fan_status")) is not True for item in shutdown_window
            )
            fan_stayed_on = shutdown_complete and shutdown_window and all(
                _is_on(item.get("fan_status")) is True for item in shutdown_window
            )

            if fan_is_off_in_window or (shutdown_complete and not fan_stayed_on):
                shutdown_violation = True
                logger.warning(
                    "event=improper_shutdown_sequence_detected machine_id=%s alert_type=%s status=alerting",
                    machine_id,
                    FAN_COMPRESSOR_SEQUENCE.shutdown_alert_type,
                )
            elif not shutdown_complete:
                shutdown_pending = True

        previous_compressor_on = current_compressor_on

    runtime_mismatch = _has_runtime_mismatch(latest_row)
    if runtime_mismatch:
        logger.warning(
            "event=fan_compressor_mismatch_detected machine_id=%s alert_type=%s status=alerting",
            machine_id,
            FAN_COMPRESSOR_SEQUENCE.runtime_alert_type,
        )
        create_alert(
            machine_id=machine_id,
            alert_type=FAN_COMPRESSOR_SEQUENCE.runtime_alert_type,
            severity=FAN_COMPRESSOR_SEQUENCE.runtime_severity,
            message="Fan must remain ON while compressor is ON.",
            metadata={
                "fan_status": latest_row.get("fan_status"),
                "compressor_status": latest_row.get("compressor_status"),
                "detected_at": latest_row["parsed_esp_log_at"].isoformat(),
            },
        )
    else:
        _resolve_if_unresolved(
            machine_id=machine_id,
            alert_type=FAN_COMPRESSOR_SEQUENCE.runtime_alert_type,
            log_message="event=fan_compressor_mismatch_resolved machine_id=%s alert_type=%s status=resolved",
        )

    if startup_violation:
        create_alert(
            machine_id=machine_id,
            alert_type=FAN_COMPRESSOR_SEQUENCE.startup_alert_type,
            severity=FAN_COMPRESSOR_SEQUENCE.startup_severity,
            message="Fan was not ON continuously for 5 minutes before compressor startup.",
            metadata={
                "required_fan_lead_seconds": int(
                    FAN_COMPRESSOR_SEQUENCE.startup_fan_lead_time.total_seconds()
                ),
            },
        )
    else:
        _resolve_if_unresolved(
            machine_id=machine_id,
            alert_type=FAN_COMPRESSOR_SEQUENCE.startup_alert_type,
            log_message="event=startup_sequence_stabilized machine_id=%s alert_type=%s status=resolved",
        )

    if shutdown_violation:
        create_alert(
            machine_id=machine_id,
            alert_type=FAN_COMPRESSOR_SEQUENCE.shutdown_alert_type,
            severity=FAN_COMPRESSOR_SEQUENCE.shutdown_severity,
            message="Fan did not remain ON for 2 minutes after compressor shutdown.",
            metadata={
                "required_fan_runout_seconds": int(
                    FAN_COMPRESSOR_SEQUENCE.shutdown_fan_run_time.total_seconds()
                ),
            },
        )
    elif not shutdown_pending:
        _resolve_if_unresolved(
            machine_id=machine_id,
            alert_type=FAN_COMPRESSOR_SEQUENCE.shutdown_alert_type,
            log_message="event=shutdown_sequence_stabilized machine_id=%s alert_type=%s status=resolved",
        )


def run_fan_compressor_sequence_validation() -> bool:
    """Validate fan/compressor startup, runtime, and shutdown sequencing."""

    try:
        now = datetime.now(UTC)
        since = now - FAN_COMPRESSOR_SEQUENCE.lookback_window
        sensor_rows = get_fan_compressor_sensor_data_since(since)
        rows_by_machine: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for row in sensor_rows:
            machine_id = row.get("machine_id")
            if not machine_id:
                logger.warning(
                    "event=sensor_row_missing_machine_id row=%s status=skipped",
                    row,
                )
                continue

            parsed_timestamp = _parse_esp_log_at(row.get("esp_log_at"))
            if parsed_timestamp is None:
                logger.warning(
                    "event=sequence_validation_row_skipped reason=invalid_timestamp row=%s status=skipped",
                    row,
                )
                continue

            normalized_row = dict(row)
            normalized_row["parsed_esp_log_at"] = parsed_timestamp
            rows_by_machine[str(machine_id)].append(normalized_row)

        for machine_id, machine_rows in rows_by_machine.items():
            machine_rows.sort(key=lambda item: item["parsed_esp_log_at"])
            _validate_machine_sequence(machine_id, machine_rows, now)
        return True
    except Exception:
        logger.exception(
            "event=automation_failed automation_id=%s status=failed",
            FAN_COMPRESSOR_SEQUENCE.automation_id,
        )
        return False
