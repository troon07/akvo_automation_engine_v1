import logging
from datetime import UTC, datetime
from typing import Any

from app.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def fetch_active_automations() -> list[dict[str, Any]]:
    """Return enabled automation definitions from Supabase."""

    try:
        client = get_supabase_client()
        response = (
            client.table("automations")
            .select("*")
            .eq("enabled", True)
            .execute()
        )
        return response.data or []
    except Exception:
        logger.exception("Failed to fetch active automations")
        return []


def get_latest_sensor_data(machine_id: str) -> dict[str, Any] | None:
    """Fetch the latest sensor data row for a machine from esp_sensor_data."""

    try:
        client = get_supabase_client()
        response = (
            client.table("esp_sensor_data")
            .select("*")
            .eq("machine_id", machine_id)
            .order("esp_log_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None
    except Exception:
        logger.exception(
            "Failed to fetch latest sensor data for machine_id=%s", machine_id
        )
        return None


def get_all_latest_machine_states() -> list[dict[str, Any]]:
    """Fetch the latest sensor row for each machine.

    This delegates the expensive grouping work to Postgres through a Supabase
    RPC named get_all_latest_machine_states. The backing SQL should use an
    indexed server-side query such as DISTINCT ON (machine_id) ordered by
    machine_id and esp_log_at descending, avoiding client-side history scans.
    """

    try:
        client = get_supabase_client()
        response = client.rpc("get_all_latest_machine_states").execute()
        data = response.data or []
        if isinstance(data, list):
            return data

        logger.warning(
            "Latest machine states RPC returned non-list payload: %s",
            type(data).__name__,
        )
        return []
    except Exception:
        logger.exception("Failed to fetch latest machine states")
        return []


def create_alert(
    machine_id: str,
    alert_type: str,
    severity: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Create an alert unless an unresolved duplicate already exists."""

    try:
        client = get_supabase_client()
        existing_response = (
            client.table("alerts")
            .select("*")
            .eq("machine_id", machine_id)
            .eq("alert_type", alert_type)
            .eq("resolved", False)
            .limit(1)
            .execute()
        )
        existing_alerts = existing_response.data or []
        if existing_alerts:
            logger.info(
                "Unresolved alert already exists for machine_id=%s alert_type=%s",
                machine_id,
                alert_type,
            )
            return existing_alerts[0]

        payload = {
            "machine_id": machine_id,
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "metadata": metadata or {},
        }
        insert_response = client.table("alerts").insert(payload).execute()
        inserted_alerts = insert_response.data or []
        return inserted_alerts[0] if inserted_alerts else None
    except Exception:
        logger.exception(
            "Failed to create alert for machine_id=%s alert_type=%s",
            machine_id,
            alert_type,
        )
        return None


def resolve_alert(machine_id: str, alert_type: str) -> dict[str, Any] | None:
    """Resolve an unresolved alert for a machine and alert type."""

    try:
        client = get_supabase_client()
        resolved_at = datetime.now(UTC).isoformat()
        response = (
            client.table("alerts")
            .update({"resolved": True,"resolved_at": resolved_at})
            .eq("machine_id", machine_id)
            .eq("alert_type", alert_type)
            .eq("resolved", False)
            .execute()
        )
        resolved_alerts = response.data or []
        if not resolved_alerts:
            logger.info(
                "No unresolved alert found for machine_id=%s alert_type=%s",
                machine_id,
                alert_type,
            )
            return None

        return resolved_alerts[0]
    except Exception:
        logger.exception(
            "Failed to resolve alert for machine_id=%s alert_type=%s",
            machine_id,
            alert_type,
        )
        return None



def has_unresolved_alert(
    machine_id: str,
    alert_type: str,
) -> bool:
    """Check whether an unresolved alert exists."""

    try:
        client = get_supabase_client()

        response = (
            client.table("alerts")
            .select("id")
            .eq("machine_id", machine_id)
            .eq("alert_type", alert_type)
            .eq("resolved", False)
            .limit(1)
            .execute()
        )

        return bool(response.data)

    except Exception:
        logger.exception(
            "Failed checking unresolved alert for "
            "machine_id=%s alert_type=%s",
            machine_id,
            alert_type,
        )

        return False