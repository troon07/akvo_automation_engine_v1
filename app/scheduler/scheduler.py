import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.automations.compressor_rapid_cycling import (
    run_compressor_rapid_cycling_detection,
)
from app.automations.fan_compressor_sequence_validation import (
    run_fan_compressor_sequence_validation,
)
from app.automations.offline_detection import run_offline_detection
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

    offline_detection_id = "offline_detection"
    register_automation_metric(offline_detection_id)
    scheduler.add_job(
        track_automation_execution(offline_detection_id, run_offline_detection),
        "interval",
        seconds=60,
        id=offline_detection_id,
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    logger.info("Registered offline detection automation")

    compressor_rapid_cycling_id = "compressor_rapid_cycling"
    register_automation_metric(compressor_rapid_cycling_id)
    scheduler.add_job(
        track_automation_execution(
            compressor_rapid_cycling_id,
            run_compressor_rapid_cycling_detection,
        ),
        "interval",
        minutes=2,
        id=compressor_rapid_cycling_id,
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    logger.info("Registered compressor rapid cycling automation")

    fan_compressor_sequence_validation_id = "fan_compressor_sequence_validation"
    register_automation_metric(fan_compressor_sequence_validation_id)
    scheduler.add_job(
        track_automation_execution(
            fan_compressor_sequence_validation_id,
            run_fan_compressor_sequence_validation,
        ),
        "interval",
        minutes=1,
        id=fan_compressor_sequence_validation_id,
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    logger.info("Registered fan/compressor sequence validation automation")


def start_scheduler() -> None:
    if scheduler.running:
        logger.debug("Scheduler already running")
        return

    register_automation_jobs()
    scheduler.start()
    logger.info("Scheduler started")


def shutdown_scheduler() -> None:
    if not scheduler.running:
        logger.debug("Scheduler already stopped")
        return

    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")
