import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.automations.compressor_rapid_cycling import (
    run_compressor_rapid_cycling_detection,
)
from app.automations.continuous_pump_runtime_detection import (
    run_continuous_pump_runtime_detection,
)
from app.automations.fan_compressor_sequence_validation import (
    run_fan_compressor_sequence_validation,
)
from app.automations.offline_detection import run_offline_detection
from app.automations.operational_integrity_validation import (
    run_operational_integrity_validation,
)
from app.automations.sensor_freeze_detection import run_sensor_freeze_detection
from app.config.automation_settings import (
    COMPRESSOR_RAPID_CYCLING,
    CONTINUOUS_PUMP_RUNTIME_DETECTION,
    FAN_COMPRESSOR_SEQUENCE,
    OFFLINE_DETECTION,
    OPERATIONAL_INTEGRITY_VALIDATION,
    SENSOR_FREEZE_DETECTION,
)
from app.config.settings import get_settings
from app.scheduler.metrics import (
    register_automation_metric,
    track_automation_execution,
)

logger = logging.getLogger(__name__)


def build_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    return AsyncIOScheduler(timezone=settings.scheduler_timezone)


scheduler = build_scheduler()


def register_automation_jobs() -> None:
    """Register recurring automation jobs with the scheduler."""

    offline_detection_id = OFFLINE_DETECTION.automation_id
    register_automation_metric(offline_detection_id)
    scheduler.add_job(
        track_automation_execution(offline_detection_id, run_offline_detection),
        "interval",
        seconds=OFFLINE_DETECTION.scheduler_interval_seconds,
        id=offline_detection_id,
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    logger.info(
        "event=automation_registered automation_id=%s interval_seconds=%s status=registered",
        offline_detection_id,
        OFFLINE_DETECTION.scheduler_interval_seconds,
    )

    compressor_rapid_cycling_id = COMPRESSOR_RAPID_CYCLING.automation_id
    register_automation_metric(compressor_rapid_cycling_id)
    scheduler.add_job(
        track_automation_execution(
            compressor_rapid_cycling_id,
            run_compressor_rapid_cycling_detection,
        ),
        "interval",
        seconds=COMPRESSOR_RAPID_CYCLING.scheduler_interval_seconds,
        id=compressor_rapid_cycling_id,
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    logger.info(
        "event=automation_registered automation_id=%s interval_seconds=%s status=registered",
        compressor_rapid_cycling_id,
        COMPRESSOR_RAPID_CYCLING.scheduler_interval_seconds,
    )

    fan_compressor_sequence_validation_id = FAN_COMPRESSOR_SEQUENCE.automation_id
    register_automation_metric(fan_compressor_sequence_validation_id)
    scheduler.add_job(
        track_automation_execution(
            fan_compressor_sequence_validation_id,
            run_fan_compressor_sequence_validation,
        ),
        "interval",
        seconds=FAN_COMPRESSOR_SEQUENCE.scheduler_interval_seconds,
        id=fan_compressor_sequence_validation_id,
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    logger.info(
        "event=automation_registered automation_id=%s interval_seconds=%s status=registered",
        fan_compressor_sequence_validation_id,
        FAN_COMPRESSOR_SEQUENCE.scheduler_interval_seconds,
    )

    operational_integrity_validation_id = (
        OPERATIONAL_INTEGRITY_VALIDATION.automation_id
    )
    register_automation_metric(operational_integrity_validation_id)
    scheduler.add_job(
        track_automation_execution(
            operational_integrity_validation_id,
            run_operational_integrity_validation,
        ),
        "interval",
        seconds=OPERATIONAL_INTEGRITY_VALIDATION.scheduler_interval_seconds,
        id=operational_integrity_validation_id,
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    logger.info(
        "event=automation_registered automation_id=%s interval_seconds=%s status=registered",
        operational_integrity_validation_id,
        OPERATIONAL_INTEGRITY_VALIDATION.scheduler_interval_seconds,
    )

    sensor_freeze_detection_id = SENSOR_FREEZE_DETECTION.automation_id
    register_automation_metric(sensor_freeze_detection_id)
    scheduler.add_job(
        track_automation_execution(
            sensor_freeze_detection_id,
            run_sensor_freeze_detection,
        ),
        "interval",
        seconds=SENSOR_FREEZE_DETECTION.scheduler_interval_seconds,
        id=sensor_freeze_detection_id,
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    logger.info(
        "event=automation_registered automation_id=%s interval_seconds=%s status=registered",
        sensor_freeze_detection_id,
        SENSOR_FREEZE_DETECTION.scheduler_interval_seconds,
    )

    continuous_pump_runtime_detection_id = (
        CONTINUOUS_PUMP_RUNTIME_DETECTION.automation_id
    )
    register_automation_metric(continuous_pump_runtime_detection_id)
    scheduler.add_job(
        track_automation_execution(
            continuous_pump_runtime_detection_id,
            run_continuous_pump_runtime_detection,
        ),
        "interval",
        seconds=CONTINUOUS_PUMP_RUNTIME_DETECTION.scheduler_interval_seconds,
        id=continuous_pump_runtime_detection_id,
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    logger.info(
        "event=automation_registered automation_id=%s interval_seconds=%s status=registered",
        continuous_pump_runtime_detection_id,
        CONTINUOUS_PUMP_RUNTIME_DETECTION.scheduler_interval_seconds,
    )


def start_scheduler() -> None:
    if scheduler.running:
        logger.debug("event=scheduler_start_skipped status=already_running")
        return

    register_automation_jobs()
    scheduler.start()
    logger.info(
        "event=scheduler_started status=running registered_automations=%s",
        len(scheduler.get_jobs()),
    )


def shutdown_scheduler() -> None:
    if not scheduler.running:
        logger.debug("event=scheduler_shutdown_skipped status=already_stopped")
        return

    scheduler.shutdown(wait=False)
    logger.info("event=scheduler_stopped status=stopped")
