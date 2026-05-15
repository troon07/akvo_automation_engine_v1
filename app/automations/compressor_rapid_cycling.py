import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from app.database.queries import (
    create_alert,
    get_sensor_data_since,
    has_unresolved_alert,
    resolve_alert,
)

logger = logging.getLogger(__name__)

ALERT_TYPE = "compressor_rapid_cycling"
ALERT_SEVERITY = "warning"
LOOKBACK_WINDOW = timedelta(minutes=10)
TRANSITION_THRESHOLD = 3


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


def run_compressor_rapid_cycling_detection() -> None:
    """Detect rapid cycling and resolve alerts after compressor behavior stabilizes."""

    try:
        since = datetime.now(UTC) - LOOKBACK_WINDOW
        sensor_rows = get_sensor_data_since(since)
        rows_by_machine: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for row in sensor_rows:
            machine_id = row.get("machine_id")
            if not machine_id:
                logger.warning("Skipping sensor row without machine_id: %s", row)
                continue

            rows_by_machine[str(machine_id)].append(row)

        for machine_id, machine_rows in rows_by_machine.items():
            transitions = _count_transitions(machine_rows)
            if transitions < TRANSITION_THRESHOLD:
                if has_unresolved_alert(
                    machine_id=machine_id,
                    alert_type=ALERT_TYPE,
                ):
                    resolved_alert = resolve_alert(
                        machine_id=machine_id,
                        alert_type=ALERT_TYPE,
                    )
                    if resolved_alert:
                        logger.info(
                            "Compressor cycling stabilized: machine_id=%s",
                            machine_id,
                        )

                continue

            logger.warning(
                "Compressor rapid cycling detected: machine_id=%s transitions=%s",
                machine_id,
                transitions,
            )
            create_alert(
                machine_id=machine_id,
                alert_type=ALERT_TYPE,
                severity=ALERT_SEVERITY,
                message="Compressor rapid cycling detected in the last 10 minutes.",
                metadata={
                    "lookback_minutes": int(LOOKBACK_WINDOW.total_seconds() / 60),
                    "transition_count": transitions,
                    "threshold": TRANSITION_THRESHOLD,
                },
            )
    except Exception:
        logger.exception("Compressor rapid cycling detection failed")
