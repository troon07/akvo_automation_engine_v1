import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.settings import get_settings
from app.scheduler.scheduler import shutdown_scheduler, start_scheduler


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
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }
