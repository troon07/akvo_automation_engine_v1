import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.settings import get_settings
from app.database.supabase_client import get_supabase_client
from app.scheduler.metrics import get_automation_metrics, get_validation_metrics
from app.scheduler.scheduler import scheduler, shutdown_scheduler, start_scheduler

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    start_scheduler()
    yield
    shutdown_scheduler()


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, object]:
    scheduler_running = scheduler.running

    try:
        get_supabase_client()
        supabase_connected = True
    except Exception:
        logger.exception("event=health_supabase_check_failed status=failed")
        supabase_connected = False

    try:
        registered_automations = len(scheduler.get_jobs())
    except Exception:
        logger.exception("event=health_scheduler_jobs_check_failed status=failed")
        registered_automations = 0

    status = "ok" if scheduler_running and supabase_connected else "degraded"

    return {
        "status": status,
        "service": settings.app_name,
        "scheduler_running": scheduler_running,
        "supabase_connected": supabase_connected,
        "registered_automations": registered_automations,
    }


@app.get("/automation-metrics", tags=["system"])
def automation_metrics() -> dict[str, object]:
    try:
        return {
            "status": "ok",
            "automations": get_automation_metrics(),
        }
    except Exception:
        logger.exception("event=automation_metrics_collection_failed status=failed")
        return {
            "status": "degraded",
            "automations": {},
        }


@app.get("/validation-metrics", tags=["system"])
def validation_metrics() -> dict[str, object]:
    try:
        return {
            "status": "ok",
            "validations": get_validation_metrics(),
        }
    except Exception:
        logger.exception("event=validation_metrics_collection_failed status=failed")
        return {
            "status": "degraded",
            "validations": {},
        }
