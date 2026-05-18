import logging

from app.config.automation_settings import OPERATIONAL_INTEGRITY_VALIDATION
from app.database.queries import get_all_latest_machine_states
from app.services.telemetry_validation import validate_latest_machine_states

logger = logging.getLogger(__name__)


def run_operational_integrity_validation() -> bool:
    """Validate latest machine telemetry states for operational integrity."""

    try:
        machine_states = get_all_latest_machine_states()
        summary = validate_latest_machine_states(machine_states)
        logger.info(
            "event=operational_integrity_validation_finished automation_id=%s machines_checked=%s violations_detected=%s alerts_created=%s alerts_resolved=%s status=success",
            OPERATIONAL_INTEGRITY_VALIDATION.automation_id,
            summary["machines_checked"],
            summary["violations_detected"],
            summary["alerts_created"],
            summary["alerts_resolved"],
        )
        return True
    except Exception:
        logger.exception(
            "event=automation_failed automation_id=%s status=failed",
            OPERATIONAL_INTEGRITY_VALIDATION.automation_id,
        )
        return False
