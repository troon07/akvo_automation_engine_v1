import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.database.queries import (
    create_alert,
    get_all_latest_machine_states,
    has_unresolved_alert,
    resolve_alert,
)

logger = logging.getLogger(__name__)

OFFLINE_ALERT_TYPE = "machine_offline"
OFFLINE_SEVERITY = "critical"
OFFLINE_THRESHOLD = timedelta(minutes=5)


def _parse_esp_log_at(value: Any) -> datetime | None:
    """Parse a Supabase timestamp value into a timezone-aware UTC datetime."""

    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, str):
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            logger.warning("Invalid esp_log_at timestamp received: %s", value)
            return None
    else:
        logger.warning("Unsupported esp_log_at value received: %r", value)
        return None

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)

    return timestamp.astimezone(UTC)


def run_offline_detection() -> None:
    """Detect offline machines and resolve offline alerts after recovery."""

    try:
        machine_states = get_all_latest_machine_states()
        now = datetime.now(UTC)

        for state in machine_states:
            machine_id = state.get("machine_id")
            esp_log_at = _parse_esp_log_at(state.get("esp_log_at"))

            if not machine_id:
                logger.warning(
                    "Skipping sensor state without machine_id: %s",
                    state,
                )
                continue

            if esp_log_at is None:
                logger.warning(
                    "Skipping offline check for machine_id=%s due to missing timestamp",
                    machine_id,
                )
                continue

            offline_duration = now - esp_log_at

            if offline_duration <= OFFLINE_THRESHOLD:

                if has_unresolved_alert(
                    machine_id=machine_id,
                    alert_type=OFFLINE_ALERT_TYPE,
                ):

                    resolved_alert = resolve_alert(
                        machine_id=machine_id,
                        alert_type=OFFLINE_ALERT_TYPE,
                    )

                    if resolved_alert:
                        logger.info(
                            "Machine recovered: machine_id=%s",
                            machine_id,
                        )

                continue

            logger.warning(
                "Machine offline detected: machine_id=%s last_seen=%s",
                machine_id,
                esp_log_at.isoformat(),
            )

            create_alert(
                machine_id=machine_id,
                alert_type=OFFLINE_ALERT_TYPE,
                severity=OFFLINE_SEVERITY,
                message="Machine is offline. No sensor data received for more than 5 minutes.",
                metadata={
                    "last_seen_at": esp_log_at.isoformat(),
                    "offline_seconds": int(
                        offline_duration.total_seconds()
                    ),
                },
            )

    except Exception:
        logger.exception("Offline detection automation failed")