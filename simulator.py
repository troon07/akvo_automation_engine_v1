import argparse
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

from app.database.supabase_client import get_supabase_client

logger = logging.getLogger("telemetry_simulator")

DEFAULT_MACHINE_ID = "machine_001"


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def base_telemetry(machine_id: str, esp_log_at: datetime) -> dict[str, Any]:
    """Build a complete esp_sensor_data payload with stable baseline values."""

    return {
        "machine_id": machine_id,
        "esp_log_at": esp_log_at.isoformat(),
        "relative_humidity": 54.0,
        "external_temperature": 27.5,
        "compressor_status": False,
        "fan_status": False,
        "lcd_status": True,
        "pump_status": False,
        "mode": "auto",
        "int_tank_full": False,
        "water_level": 68.0,
        "voltage": 230.0,
        "current": 1.2,
        "watts": 276.0,
        "wifi_strength": -58,
        "fault_code": None,
    }


def row_at(
    machine_id: str,
    now: datetime,
    minutes_ago: int,
    **overrides: Any,
) -> dict[str, Any]:
    """Create a telemetry row at a deterministic offset from now."""

    payload = base_telemetry(machine_id, now - timedelta(minutes=minutes_ago))
    payload.update(overrides)
    return payload


def normal_operation(machine_id: str, now: datetime) -> list[dict[str, Any]]:
    """Simulate proper fan lead, compressor runtime, and fan cooldown."""

    return [
        row_at(machine_id, now, 9, fan_status=True, compressor_status=False),
        row_at(machine_id, now, 8, fan_status=True, compressor_status=False),
        row_at(machine_id, now, 7, fan_status=True, compressor_status=False),
        row_at(machine_id, now, 6, fan_status=True, compressor_status=False),
        row_at(machine_id, now, 5, fan_status=True, compressor_status=False),
        row_at(
            machine_id,
            now,
            4,
            fan_status=True,
            compressor_status=True,
            current=5.6,
            watts=1288.0,
        ),
        row_at(
            machine_id,
            now,
            3,
            fan_status=True,
            compressor_status=False,
            current=1.8,
            watts=414.0,
        ),
        row_at(machine_id, now, 2, fan_status=True, compressor_status=False),
        row_at(machine_id, now, 1, fan_status=True, compressor_status=False),
        row_at(machine_id, now, 0, fan_status=False, compressor_status=False),
    ]


def offline(machine_id: str, now: datetime) -> list[dict[str, Any]]:
    """Simulate a machine that stopped sending telemetry more than 5 minutes ago."""

    return [
        row_at(machine_id, now, 9, fan_status=True, compressor_status=False),
        row_at(
            machine_id,
            now,
            8,
            fan_status=True,
            compressor_status=True,
            current=5.4,
            watts=1242.0,
        ),
        row_at(
            machine_id,
            now,
            7,
            fan_status=True,
            compressor_status=True,
            current=5.5,
            watts=1265.0,
            wifi_strength=-72,
        ),
    ]


def rapid_cycling(machine_id: str, now: datetime) -> list[dict[str, Any]]:
    """Simulate repeated compressor ON/OFF transitions in 10 minutes."""

    return [
        row_at(machine_id, now, 8, fan_status=True, compressor_status=False),
        row_at(
            machine_id,
            now,
            7,
            fan_status=True,
            compressor_status=True,
            current=5.7,
            watts=1311.0,
        ),
        row_at(machine_id, now, 6, fan_status=True, compressor_status=False),
        row_at(
            machine_id,
            now,
            5,
            fan_status=True,
            compressor_status=True,
            current=5.8,
            watts=1334.0,
        ),
        row_at(machine_id, now, 4, fan_status=True, compressor_status=False),
        row_at(
            machine_id,
            now,
            3,
            fan_status=True,
            compressor_status=True,
            current=5.7,
            watts=1311.0,
        ),
        row_at(machine_id, now, 2, fan_status=True, compressor_status=False),
        row_at(machine_id, now, 1, fan_status=True, compressor_status=False),
    ]


def fan_mismatch(machine_id: str, now: datetime) -> list[dict[str, Any]]:
    """Simulate compressor running while fan is OFF."""

    return [
        row_at(machine_id, now, 5, fan_status=True, compressor_status=False),
        row_at(machine_id, now, 4, fan_status=True, compressor_status=False),
        row_at(machine_id, now, 3, fan_status=True, compressor_status=False),
        row_at(machine_id, now, 2, fan_status=True, compressor_status=True),
        row_at(
            machine_id,
            now,
            1,
            fan_status=False,
            compressor_status=True,
            current=6.1,
            watts=1403.0,
            fault_code="FAN_STOPPED",
        ),
        row_at(
            machine_id,
            now,
            0,
            fan_status=False,
            compressor_status=True,
            current=6.2,
            watts=1426.0,
            fault_code="FAN_STOPPED",
        ),
    ]


def improper_startup(machine_id: str, now: datetime) -> list[dict[str, Any]]:
    """Simulate compressor startup before the required fan lead time."""

    return [
        row_at(machine_id, now, 6, fan_status=False, compressor_status=False),
        row_at(machine_id, now, 5, fan_status=False, compressor_status=False),
        row_at(machine_id, now, 4, fan_status=True, compressor_status=False),
        row_at(
            machine_id,
            now,
            3,
            fan_status=True,
            compressor_status=True,
            current=5.9,
            watts=1357.0,
        ),
        row_at(
            machine_id,
            now,
            2,
            fan_status=True,
            compressor_status=True,
            current=5.8,
            watts=1334.0,
        ),
        row_at(
            machine_id,
            now,
            1,
            fan_status=True,
            compressor_status=True,
            current=5.7,
            watts=1311.0,
        ),
    ]


def improper_shutdown(machine_id: str, now: datetime) -> list[dict[str, Any]]:
    """Simulate fan stopping too early after compressor shutdown."""

    return [
        row_at(machine_id, now, 7, fan_status=True, compressor_status=False),
        row_at(machine_id, now, 6, fan_status=True, compressor_status=False),
        row_at(machine_id, now, 5, fan_status=True, compressor_status=False),
        row_at(
            machine_id,
            now,
            4,
            fan_status=True,
            compressor_status=True,
            current=5.6,
            watts=1288.0,
        ),
        row_at(machine_id, now, 3, fan_status=True, compressor_status=False),
        row_at(machine_id, now, 2, fan_status=False, compressor_status=False),
        row_at(machine_id, now, 1, fan_status=False, compressor_status=False),
        row_at(machine_id, now, 0, fan_status=False, compressor_status=False),
    ]


SCENARIOS: dict[str, Callable[[str, datetime], list[dict[str, Any]]]] = {
    "normal_operation": normal_operation,
    "offline": offline,
    "rapid_cycling": rapid_cycling,
    "fan_mismatch": fan_mismatch,
    "improper_startup": improper_startup,
    "improper_shutdown": improper_shutdown,
}


def insert_telemetry(rows: list[dict[str, Any]]) -> None:
    """Insert telemetry rows into Supabase and log what was sent."""

    if not rows:
        logger.warning("event=telemetry_generation_empty status=skipped")
        return

    client = get_supabase_client()
    response = client.table("esp_sensor_data").insert(rows).execute()
    inserted_count = len(response.data or rows)

    for row in rows:
        logger.info(
            "event=telemetry_inserted machine_id=%s esp_log_at=%s fan_status=%s compressor_status=%s mode=%s fault_code=%s status=inserted",
            row["machine_id"],
            row["esp_log_at"],
            row["fan_status"],
            row["compressor_status"],
            row["mode"],
            row["fault_code"],
        )

    logger.info(
        "event=telemetry_batch_inserted inserted_count=%s status=success",
        inserted_count,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic test telemetry for automation rules."
    )
    parser.add_argument(
        "--scenario",
        required=True,
        choices=sorted(SCENARIOS),
        help="Telemetry scenario to simulate.",
    )
    parser.add_argument(
        "--machine-id",
        default=DEFAULT_MACHINE_ID,
        help=f"Machine id to simulate. Defaults to {DEFAULT_MACHINE_ID}.",
    )
    return parser.parse_args()


def main() -> int:
    configure_logging()
    args = parse_args()

    try:
        now = datetime.now(UTC).replace(microsecond=0)
        rows = SCENARIOS[args.scenario](args.machine_id, now)

        logger.info(
            "event=telemetry_scenario_started scenario=%s machine_id=%s status=running",
            args.scenario,
            args.machine_id,
        )
        insert_telemetry(rows)
        logger.info(
            "event=telemetry_scenario_finished scenario=%s machine_id=%s status=success",
            args.scenario,
            args.machine_id,
        )
        return 0
    except Exception:
        logger.exception(
            "event=telemetry_simulation_failed scenario=%s machine_id=%s status=failed",
            args.scenario,
            args.machine_id,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
