import logging
from datetime import datetime
from typing import Any

from app.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def log_automation_execution(
    automation_name: str,
    started_at: datetime,
    completed_at: datetime,
    execution_duration_ms: float | int,
    analyzed_machine_count: int,
    detection_count: int,
    status: str,
    error_message: str | None = None,
) -> None:
    """Persist a lightweight automation execution summary."""

    duration_ms = int(round(execution_duration_ms))

    payload: dict[str, Any] = {
        "automation_name": automation_name,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "execution_duration_ms": duration_ms,
        "analyzed_machine_count": analyzed_machine_count,
        "detection_count": detection_count,
        "status": status,
        "error_message": error_message,
    }

    try:
        client = get_supabase_client()
        client.table("automation_execution_logs").insert(payload).execute()
        logger.debug(
            "event=automation_execution_log_inserted automation_id=%s status=%s execution_duration_ms=%s",
            automation_name,
            status,
            duration_ms,
        )
    except Exception:
        logger.exception(
            "event=automation_execution_log_insert_failed automation_id=%s status=failed",
            automation_name,
        )
