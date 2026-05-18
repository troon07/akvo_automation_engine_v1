import logging
from datetime import UTC, datetime
from typing import Any

from app.config.automation_settings import OFFLINE_DETECTION
from app.database.queries import (
    create_alert,
    get_all_latest_machine_states,
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


def run_offline_detection() -> bool:
    """Detect offline machines and resolve offline alerts after recovery."""

    try:
        machine_states = get_all_latest_machine_states()
        now = datetime.now(UTC)

        for state in machine_states:
            machine_id = state.get("machine_id")
            esp_log_at = _parse_esp_log_at(state.get("esp_log_at"))

            if not machine_id:
                logger.warning(
                    "event=sensor_state_missing_machine_id state=%s status=skipped",
                    state,
                )
                continue

            if esp_log_at is None:
                logger.warning(
                    "event=offline_check_skipped machine_id=%s reason=missing_timestamp status=skipped",
                    machine_id,
                )
                continue

            offline_duration = now - esp_log_at

            if offline_duration <= OFFLINE_DETECTION.offline_threshold:

                if has_unresolved_alert(
                    machine_id=machine_id,
                    alert_type=OFFLINE_DETECTION.alert_type,
                ):

                    resolved_alert = resolve_alert(
                        machine_id=machine_id,
                        alert_type=OFFLINE_DETECTION.alert_type,
                    )

                    if resolved_alert:
                        logger.info(
                            "event=machine_recovered machine_id=%s alert_type=%s status=resolved",
                            machine_id,
                            OFFLINE_DETECTION.alert_type,
                        )

                continue

            logger.warning(
                "event=machine_offline_detected machine_id=%s alert_type=%s offline_seconds=%s last_seen_at=%s status=alerting",
                machine_id,
                OFFLINE_DETECTION.alert_type,
                int(offline_duration.total_seconds()),
                esp_log_at.isoformat(),
            )

            create_alert(
                machine_id=machine_id,
                alert_type=OFFLINE_DETECTION.alert_type,
                severity=OFFLINE_DETECTION.severity,
                message="Machine is offline. No sensor data received for more than 5 minutes.",
                metadata={
                    "last_seen_at": esp_log_at.isoformat(),
                    "offline_seconds": int(
                        offline_duration.total_seconds()
                    ),
                },
            )

        return True
    except Exception:
        logger.exception(
            "event=automation_failed automation_id=%s status=failed",
            OFFLINE_DETECTION.automation_id,
        )
        return False
