import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
