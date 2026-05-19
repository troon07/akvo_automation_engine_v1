import logging
from collections.abc import Callable
from datetime import UTC, datetime
from threading import Lock
from time import perf_counter
from typing import Any

logger = logging.getLogger(__name__)

_metrics_lock = Lock()
_automation_metrics: dict[str, dict[str, Any]] = {}
_validation_metrics: dict[str, dict[str, Any]] = {}


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


def register_validation_metric(alert_type: str) -> None:
    """Ensure a metrics entry exists for a validation alert type."""

    with _metrics_lock:
        _validation_metrics.setdefault(
            alert_type,
            {
                "detection_count": 0,
                "resolution_count": 0,
                "active_machines": set(),
                "affected_machines": set(),
                "last_detected_at": None,
            },
        )


def record_validation_detection(alert_type: str, machine_id: str) -> None:
    """Record a newly created validation alert."""

    machine_id = str(machine_id)

    with _metrics_lock:
        register_needed = alert_type not in _validation_metrics

    if register_needed:
        register_validation_metric(alert_type)

    with _metrics_lock:
        metrics = _validation_metrics[alert_type]
        metrics["detection_count"] += 1
        metrics["active_machines"].add(machine_id)
        metrics["affected_machines"].add(machine_id)
        metrics["last_detected_at"] = _utc_now_iso()
        logger.debug(
            "event=validation_metric_detection_recorded machine_id=%s alert_type=%s active_count=%s status=recorded",
            machine_id,
            alert_type,
            len(metrics["active_machines"]),
        )


def record_validation_resolution(alert_type: str, machine_id: str) -> None:
    """Record a resolved validation alert."""

    machine_id = str(machine_id)

    with _metrics_lock:
        register_needed = alert_type not in _validation_metrics

    if register_needed:
        register_validation_metric(alert_type)

    with _metrics_lock:
        metrics = _validation_metrics[alert_type]
        metrics["resolution_count"] += 1
        metrics["active_machines"].discard(machine_id)
        metrics["affected_machines"].add(machine_id)
        logger.debug(
            "event=validation_metric_resolution_recorded machine_id=%s alert_type=%s active_count=%s status=recorded",
            machine_id,
            alert_type,
            len(metrics["active_machines"]),
        )


def get_validation_metrics() -> dict[str, dict[str, Any]]:
    """Return a JSON-safe snapshot of validation metrics."""

    with _metrics_lock:
        return {
            alert_type: {
                "detection_count": metrics["detection_count"],
                "resolution_count": metrics["resolution_count"],
                "active_count": len(metrics["active_machines"]),
                "affected_machine_count": len(metrics["affected_machines"]),
                "last_detected_at": metrics["last_detected_at"],
            }
            for alert_type, metrics in _validation_metrics.items()
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
            logger.exception(
                "event=automation_execution_failed automation_id=%s execution_duration_ms=%s status=failed",
                automation_id,
                duration_ms,
            )
            raise

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        if result is False:
            _record_failure(automation_id, duration_ms)
            logger.warning(
                "event=automation_execution_finished automation_id=%s execution_duration_ms=%s status=failed",
                automation_id,
                duration_ms,
            )
        else:
            with _metrics_lock:
                metrics = _automation_metrics[automation_id]
                metrics["last_success_at"] = _utc_now_iso()
                metrics["execution_duration_ms"] = duration_ms
            logger.info(
                "event=automation_execution_finished automation_id=%s execution_duration_ms=%s status=success",
                automation_id,
                duration_ms,
            )

        return result

    return wrapped_job


def _record_failure(automation_id: str, duration_ms: float) -> None:
    with _metrics_lock:
        metrics = _automation_metrics[automation_id]
        metrics["failure_count"] += 1
        metrics["last_failure_at"] = _utc_now_iso()
        metrics["execution_duration_ms"] = duration_ms
