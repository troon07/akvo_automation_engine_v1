import logging
from typing import Any

from app.config.validation_settings import VALIDATION_SETTINGS
from app.database.queries import create_alert, has_unresolved_alert, resolve_alert
from app.scheduler.metrics import (
    record_validation_detection,
    record_validation_resolution,
    register_validation_metric,
)

logger = logging.getLogger(__name__)

SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

ALERT_INVALID_HUMIDITY = "validation_invalid_humidity"
ALERT_INVALID_VOLTAGE = "validation_invalid_voltage"
ALERT_INVALID_CURRENT = "validation_invalid_current"
ALERT_INVALID_WATTS = "validation_invalid_watts"
ALERT_POWER_STATE_MISMATCH = "validation_power_state_mismatch"
ALERT_PUMP_TANK_CONFLICT = "validation_pump_tank_conflict"

VALIDATION_ALERT_TYPES = (
    ALERT_INVALID_HUMIDITY,
    ALERT_INVALID_VOLTAGE,
    ALERT_INVALID_CURRENT,
    ALERT_INVALID_WATTS,
    ALERT_POWER_STATE_MISMATCH,
    ALERT_PUMP_TANK_CONFLICT,
)

for validation_alert_type in VALIDATION_ALERT_TYPES:
    register_validation_metric(validation_alert_type)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_on(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return bool(value)

    if isinstance(value, str):
        return value.strip().lower() in {"on", "true", "1", "running", "enabled"}

    return False


def _sync_validation_alert(
    machine_id: str,
    alert_type: str,
    severity: str,
    violation_detected: bool,
    message: str,
    metadata: dict[str, Any],
) -> tuple[int, int, int]:
    """Create or resolve a validation alert while avoiding duplicate requests."""

    unresolved_exists = has_unresolved_alert(
        machine_id=machine_id,
        alert_type=alert_type,
    )

    if violation_detected:
        if unresolved_exists:
            return 1, 0, 0

        logger.warning(
            "event=operational_integrity_violation_detected machine_id=%s alert_type=%s severity=%s status=alerting",
            machine_id,
            alert_type,
            severity,
        )
        created_alert = create_alert(
            machine_id=machine_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            metadata=metadata,
        )
        if created_alert:
            record_validation_detection(alert_type=alert_type, machine_id=machine_id)

        return 1, 1 if created_alert else 0, 0

    if not unresolved_exists:
        return 0, 0, 0

    resolve_alert(machine_id=machine_id, alert_type=alert_type)
    still_unresolved = has_unresolved_alert(
        machine_id=machine_id,
        alert_type=alert_type,
    )

    if not still_unresolved:
        record_validation_resolution(alert_type=alert_type, machine_id=machine_id)
        logger.info(
            "event=operational_integrity_violation_resolved machine_id=%s alert_type=%s status=resolved",
            machine_id,
            alert_type,
        )
        return 0, 0, 1

    logger.debug(
        "event=operational_integrity_violation_resolution_pending machine_id=%s alert_type=%s status=pending",
        machine_id,
        alert_type,
    )
    return 0, 0, 0


def validate_latest_machine_states(
    machine_states: list[dict[str, Any]],
) -> dict[str, int]:
    """Validate latest telemetry state for each machine and sync validation alerts."""

    summary = {
        "machines_checked": 0,
        "violations_detected": 0,
        "alerts_created": 0,
        "alerts_resolved": 0,
    }

    for state in machine_states:
        machine_id = state.get("machine_id")
        if not machine_id:
            logger.warning(
                "event=validation_state_missing_machine_id state=%s status=skipped",
                state,
            )
            continue

        machine_id = str(machine_id)
        summary["machines_checked"] += 1

        humidity = _as_float(state.get("relative_humidity"))
        voltage = _as_float(state.get("voltage"))
        current = _as_float(state.get("current"))
        watts = _as_float(state.get("watts"))
        compressor_on = _is_on(state.get("compressor_status"))
        pump_on = _is_on(state.get("pump_status"))
        tank_full = _is_on(state.get("int_tank_full"))

        checks = [
            (
                ALERT_INVALID_HUMIDITY,
                SEVERITY_WARNING,
                humidity is not None
                and (
                    humidity < VALIDATION_SETTINGS.humidity_min
                    or humidity > VALIDATION_SETTINGS.humidity_max
                ),
                "Humidity reading is outside the valid operating range.",
                {
                    "category": "sensor_range_integrity",
                    "relative_humidity": humidity,
                    "min": VALIDATION_SETTINGS.humidity_min,
                    "max": VALIDATION_SETTINGS.humidity_max,
                },
            ),
            (
                ALERT_INVALID_VOLTAGE,
                SEVERITY_WARNING,
                voltage is not None
                and (
                    voltage < VALIDATION_SETTINGS.voltage_min
                    or voltage > VALIDATION_SETTINGS.voltage_max
                ),
                "Voltage reading is outside the configured valid range.",
                {
                    "category": "sensor_range_integrity",
                    "voltage": voltage,
                    "min": VALIDATION_SETTINGS.voltage_min,
                    "max": VALIDATION_SETTINGS.voltage_max,
                },
            ),
            (
                ALERT_INVALID_CURRENT,
                SEVERITY_WARNING,
                current is not None and current < 0,
                "Current reading cannot be negative.",
                {
                    "category": "sensor_range_integrity",
                    "current": current,
                },
            ),
            (
                ALERT_INVALID_WATTS,
                SEVERITY_WARNING,
                watts is not None and watts < 0,
                "Watts reading cannot be negative.",
                {
                    "category": "sensor_range_integrity",
                    "watts": watts,
                },
            ),
            (
                ALERT_POWER_STATE_MISMATCH,
                SEVERITY_CRITICAL,
                compressor_on
                and (
                    (watts is not None and watts < VALIDATION_SETTINGS.compressor_min_watts)
                    or (
                        current is not None
                        and current < VALIDATION_SETTINGS.compressor_min_current
                    )
                ),
                "Compressor is ON but electrical load is below the configured minimum.",
                {
                    "category": "physical_state_contradiction",
                    "compressor_status": state.get("compressor_status"),
                    "watts": watts,
                    "current": current,
                    "minimum_watts": VALIDATION_SETTINGS.compressor_min_watts,
                    "minimum_current": VALIDATION_SETTINGS.compressor_min_current,
                },
            ),
            (
                ALERT_PUMP_TANK_CONFLICT,
                SEVERITY_CRITICAL,
                pump_on and tank_full,
                "Pump is ON while internal tank is already full.",
                {
                    "category": "physical_state_contradiction",
                    "pump_status": state.get("pump_status"),
                    "int_tank_full": state.get("int_tank_full"),
                },
            ),
        ]

        for alert_type, severity, violation_detected, message, metadata in checks:
            detected, created, resolved = _sync_validation_alert(
                machine_id=machine_id,
                alert_type=alert_type,
                severity=severity,
                violation_detected=violation_detected,
                message=message,
                metadata=metadata,
            )
            summary["violations_detected"] += detected
            summary["alerts_created"] += created
            summary["alerts_resolved"] += resolved

    return summary
