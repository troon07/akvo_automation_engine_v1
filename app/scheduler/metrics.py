import logging
from collections.abc import Callable
from datetime import UTC, datetime
from threading import Lock
from time import perf_counter
from typing import Any

logger = logging.getLogger(__name__)

_metrics_lock = Lock()
_automation_metrics: dict[str, dict[str, Any]] = {}


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def register_automation_metric(automation_id: str) -> None:
    """Ensure a metrics entry exists for an automation job."""

    with _metrics_lock:
        _automation_metrics.setdefault(
            automation_id,
            {
                "execution_count": 0,
                "failure_count": 0,
                "last_run_at": None,
                "last_success_at": None,
                "last_failure_at": None,
                "execution_duration_ms": None,
            },
        )


def get_automation_metrics() -> dict[str, dict[str, Any]]:
    """Return a snapshot of automation execution metrics."""

    with _metrics_lock:
        return {
            automation_id: dict(metrics)
            for automation_id, metrics in _automation_metrics.items()
        }


def track_automation_execution(
    automation_id: str,
    job_func: Callable[[], Any],
) -> Callable[[], Any]:
    """Wrap an automation job so execution metrics are recorded automatically."""

    register_automation_metric(automation_id)

    def wrapped_job() -> Any:
        started_at = perf_counter()

        with _metrics_lock:
            metrics = _automation_metrics[automation_id]
            metrics["execution_count"] += 1
            metrics["last_run_at"] = _utc_now_iso()

        try:
            result = job_func()
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            _record_failure(automation_id, duration_ms)
            logger.exception("Automation job failed: automation_id=%s", automation_id)
            raise

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        if result is False:
            _record_failure(automation_id, duration_ms)
        else:
            with _metrics_lock:
                metrics = _automation_metrics[automation_id]
                metrics["last_success_at"] = _utc_now_iso()
                metrics["execution_duration_ms"] = duration_ms

        return result

    return wrapped_job


def _record_failure(automation_id: str, duration_ms: float) -> None:
    with _metrics_lock:
        metrics = _automation_metrics[automation_id]
        metrics["failure_count"] += 1
        metrics["last_failure_at"] = _utc_now_iso()
        metrics["execution_duration_ms"] = duration_ms
