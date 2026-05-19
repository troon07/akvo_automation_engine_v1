import logging
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from app.config.automation_settings import COMPRESSOR_RAPID_CYCLING
from app.database.queries import (
    create_alert,
    get_sensor_data_since,
    has_unresolved_alert,
    resolve_alert,
)
from app.services.automation_execution_logger import log_automation_execution

logger = logging.getLogger(__name__)


def _normalize_compressor_status(value: Any) -> str | None:
    """Normalize compressor status values for transition detection."""

    if value is None:
        return None

    if isinstance(value, bool):
        return "on" if value else "off"

    return str(value).strip().lower()


def _count_transitions(rows: list[dict[str, Any]]) -> int:
    """Count compressor status transitions in timestamp-ordered sensor rows."""

    transitions = 0
    previous_status: str | None = None

    for row in rows:
        current_status = _normalize_compressor_status(row.get("compressor_status"))
        if current_status is None:
            continue

        if previous_status is not None and current_status != previous_status:
            transitions += 1

        previous_status = current_status

    return transitions


def run_compressor_rapid_cycling_detection() -> bool:
    """Detect rapid cycling and resolve alerts after compressor behavior stabilizes."""

    started_at = datetime.now(UTC)
    analyzed_machine_count = 0
    detection_count = 0

    try:
        since = datetime.now(UTC) - COMPRESSOR_RAPID_CYCLING.lookback_window
        sensor_rows = get_sensor_data_since(since)
        rows_by_machine: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for row in sensor_rows:
            machine_id = row.get("machine_id")
            if not machine_id:
                logger.warning(
                    "event=sensor_row_missing_machine_id row=%s status=skipped",
                    row,
                )
                continue

            rows_by_machine[str(machine_id)].append(row)

        for machine_id, machine_rows in rows_by_machine.items():
            analyzed_machine_count += 1
            transitions = _count_transitions(machine_rows)
            if transitions < COMPRESSOR_RAPID_CYCLING.transition_threshold:
                if has_unresolved_alert(
                    machine_id=machine_id,
                    alert_type=COMPRESSOR_RAPID_CYCLING.alert_type,
                ):
                    resolved_alert = resolve_alert(
                        machine_id=machine_id,
                        alert_type=COMPRESSOR_RAPID_CYCLING.alert_type,
                    )
                    if resolved_alert:
                        logger.info(
                            "event=compressor_cycling_stabilized machine_id=%s alert_type=%s transitions=%s status=resolved",
                            machine_id,
                            COMPRESSOR_RAPID_CYCLING.alert_type,
                            transitions,
                        )

                continue

            logger.warning(
                "event=compressor_rapid_cycling_detected machine_id=%s alert_type=%s transitions=%s threshold=%s status=alerting",
                machine_id,
                COMPRESSOR_RAPID_CYCLING.alert_type,
                transitions,
                COMPRESSOR_RAPID_CYCLING.transition_threshold,
            )
            detection_count += 1
            create_alert(
                machine_id=machine_id,
                alert_type=COMPRESSOR_RAPID_CYCLING.alert_type,
                severity=COMPRESSOR_RAPID_CYCLING.severity,
                message="Compressor rapid cycling detected in the last 10 minutes.",
                metadata={
                    "lookback_minutes": int(
                        COMPRESSOR_RAPID_CYCLING.lookback_window.total_seconds() / 60
                    ),
                    "transition_count": transitions,
                    "threshold": COMPRESSOR_RAPID_CYCLING.transition_threshold,
                },
            )
        completed_at = datetime.now(UTC)
        log_automation_execution(
            automation_name=COMPRESSOR_RAPID_CYCLING.automation_id,
            started_at=started_at,
            completed_at=completed_at,
            execution_duration_ms=round(
                (completed_at - started_at).total_seconds() * 1000,
                2,
            ),
            analyzed_machine_count=analyzed_machine_count,
            detection_count=detection_count,
            status="success",
        )
        return True
    except Exception as exc:
        completed_at = datetime.now(UTC)
        log_automation_execution(
            automation_name=COMPRESSOR_RAPID_CYCLING.automation_id,
            started_at=started_at,
            completed_at=completed_at,
            execution_duration_ms=round(
                (completed_at - started_at).total_seconds() * 1000,
                2,
            ),
            analyzed_machine_count=analyzed_machine_count,
            detection_count=detection_count,
            status="failed",
            error_message=str(exc),
        )
        logger.exception(
            "event=automation_failed automation_id=%s status=failed",
            COMPRESSOR_RAPID_CYCLING.automation_id,
        )
        return False
