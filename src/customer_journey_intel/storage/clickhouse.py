from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from customer_journey_intel.common.settings import Settings

RAW_EVENT_COLUMNS = [
    "event_id",
    "event_name",
    "occurred_at",
    "received_at",
    "customer_id",
    "anonymous_id",
    "session_id",
    "journey_stage",
    "channel",
    "experiment_id",
    "variant_id",
    "properties",
]


def build_raw_events_ddl(database: str = "customer_journey") -> str:
    return f"""
CREATE TABLE IF NOT EXISTS {database}.raw_events
(
    event_id        String,
    event_name      LowCardinality(String),
    occurred_at     DateTime64(3, 'UTC'),
    received_at     DateTime64(3, 'UTC'),
    customer_id     Nullable(String),
    anonymous_id    Nullable(String),
    session_id      String,
    journey_stage   LowCardinality(String),
    channel         LowCardinality(String),
    experiment_id   Nullable(String),
    variant_id      Nullable(String),
    properties      String,
    ingest_date     Date DEFAULT toDate(occurred_at)
)
ENGINE = MergeTree
PARTITION BY ingest_date
ORDER BY (occurred_at, session_id, event_id)
TTL ingest_date + INTERVAL 90 DAY
""".strip()


def _parse_clickhouse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _row_from_event(event: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(event["event_id"]),
        str(event["event_name"]),
        _parse_clickhouse_datetime(event["occurred_at"]),
        _parse_clickhouse_datetime(event["received_at"]),
        event.get("customer_id"),
        event.get("anonymous_id"),
        str(event["session_id"]),
        str(event["journey_stage"]),
        str(event["channel"]),
        event.get("experiment_id"),
        event.get("variant_id"),
        json.dumps(event.get("properties", {}), sort_keys=True),
    )


def insert_raw_events_jsonl(
    client: Any,
    lines: Iterable[str],
    database: str = "customer_journey",
) -> int:
    """Create the raw event table and insert JSON Lines events into ClickHouse."""

    client.command(build_raw_events_ddl(database=database))
    rows = [_row_from_event(json.loads(line)) for line in lines if line.strip()]
    if not rows:
        return 0
    client.insert(
        f"{database}.raw_events",
        rows,
        column_names=RAW_EVENT_COLUMNS,
    )
    return len(rows)


def create_client(settings: Settings | None = None) -> Any:
    from clickhouse_connect import get_client

    runtime_settings = settings or Settings()
    return get_client(
        host=runtime_settings.clickhouse_host,
        port=runtime_settings.clickhouse_port,
        database=runtime_settings.clickhouse_database,
    )


def load_jsonl_file(path: Path, settings: Settings | None = None) -> int:
    runtime_settings = settings or Settings()
    client = create_client(runtime_settings)
    with path.open(encoding="utf-8") as handle:
        return insert_raw_events_jsonl(
            client=client,
            lines=handle,
            database=runtime_settings.clickhouse_database,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Load journey JSONL into ClickHouse raw_events.")
    parser.add_argument("--input", type=Path, default=Path("data/sample_events.jsonl"))
    args = parser.parse_args()

    count = load_jsonl_file(args.input)
    print(f"loaded {count} events into ClickHouse raw_events")


if __name__ == "__main__":
    main()
