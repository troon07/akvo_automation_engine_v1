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

logger = logging.getLogger(__name__)


def build_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    return AsyncIOScheduler(timezone=settings.scheduler_timezone)


scheduler = build_scheduler()


def register_automation_jobs() -> None:
    """Register recurring automation jobs with the scheduler."""

    scheduler.add_job(
        run_offline_detection,
        "interval",
        seconds=60,
        id="offline_detection",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    logger.info("Registered offline detection automation")

    scheduler.add_job(
        run_compressor_rapid_cycling_detection,
        "interval",
        minutes=2,
        id="compressor_rapid_cycling",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    logger.info("Registered compressor rapid cycling automation")

    scheduler.add_job(
        run_fan_compressor_sequence_validation,
        "interval",
        minutes=1,
        id="fan_compressor_sequence_validation",
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
