from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from customer_journey_intel.common.logging import configure_logging
from customer_journey_intel.common.settings import Settings
from customer_journey_intel.streaming.aggregates import (
    compute_experiment_batch,
    compute_funnel_batch,
    compute_revenue_events,
    compute_session_metrics,
)

FUNNEL_METRIC_COLUMNS = [
    "window_start",
    "window_end",
    "journey_stage",
    "event_name",
    "session_count",
    "event_count",
    "experiment_id",
    "variant_id",
]
SESSION_METRIC_COLUMNS = [
    "session_id",
    "customer_id",
    "anonymous_id",
    "channel",
    "first_seen",
    "last_seen",
    "event_count",
    "max_journey_stage",
    "reached_checkout",
    "reached_payment",
    "converted",
    "funnel_collapse",
    "cart_value_at_abandon",
]
REVENUE_EVENT_COLUMNS = [
    "event_id",
    "session_id",
    "customer_id",
    "event_name",
    "occurred_at",
    "cart_value",
    "product_id",
    "order_id",
    "payment_method",
    "failure_reason",
    "leakage",
    "resolution",
    "experiment_id",
    "variant_id",
]
EXPERIMENT_METRIC_COLUMNS = [
    "window_start",
    "window_end",
    "experiment_id",
    "variant_id",
    "assigned_sessions",
    "exposed_sessions",
    "converted_sessions",
]

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

logger = logging.getLogger(__name__)


def build_database_ddl(database: str = "customer_journey") -> str:
    return f"CREATE DATABASE IF NOT EXISTS {database}"


def build_funnel_metrics_ddl(database: str = "customer_journey") -> str:
    return f"""
CREATE TABLE IF NOT EXISTS {database}.funnel_metrics
(
    window_start    DateTime64(3, 'UTC'),
    window_end      DateTime64(3, 'UTC'),
    journey_stage   LowCardinality(String),
    event_name      LowCardinality(String),
    session_count   UInt64,
    event_count     UInt64,
    experiment_id   LowCardinality(String),
    variant_id      LowCardinality(String),
    computed_at     DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(computed_at)
PARTITION BY toDate(window_start)
ORDER BY (window_start, journey_stage, event_name, experiment_id, variant_id)
TTL toDate(window_start) + INTERVAL 90 DAY
""".strip()


def build_session_metrics_ddl(database: str = "customer_journey") -> str:
    return f"""
CREATE TABLE IF NOT EXISTS {database}.session_metrics
(
    session_id          String,
    customer_id         Nullable(String),
    anonymous_id        Nullable(String),
    channel             LowCardinality(String),
    first_seen          DateTime64(3, 'UTC'),
    last_seen           DateTime64(3, 'UTC'),
    event_count         UInt32,
    max_journey_stage   LowCardinality(String),
    reached_checkout    UInt8,
    reached_payment     UInt8,
    converted           UInt8,
    funnel_collapse     UInt8,
    cart_value_at_abandon Nullable(Float64),
    updated_at          DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toDate(first_seen)
ORDER BY (session_id)
TTL toDate(first_seen) + INTERVAL 90 DAY
""".strip()


def build_revenue_events_ddl(database: str = "customer_journey") -> str:
    return f"""
CREATE TABLE IF NOT EXISTS {database}.revenue_events
(
    event_id        String,
    session_id      String,
    customer_id     Nullable(String),
    event_name      LowCardinality(String),
    occurred_at     DateTime64(3, 'UTC'),
    cart_value      Nullable(Float64),
    product_id      Nullable(String),
    order_id        Nullable(String),
    payment_method  Nullable(String),
    failure_reason  Nullable(String),
    leakage         UInt8,
    resolution      LowCardinality(String),
    experiment_id   LowCardinality(String),
    variant_id      LowCardinality(String),
    ingest_date     Date DEFAULT toDate(occurred_at)
)
ENGINE = ReplacingMergeTree()
PARTITION BY ingest_date
ORDER BY (occurred_at, session_id, event_id)
TTL ingest_date + INTERVAL 90 DAY
""".strip()


def build_experiment_metrics_ddl(database: str = "customer_journey") -> str:
    return f"""
CREATE TABLE IF NOT EXISTS {database}.experiment_metrics
(
    window_start        DateTime64(3, 'UTC'),
    window_end          DateTime64(3, 'UTC'),
    experiment_id       LowCardinality(String),
    variant_id          LowCardinality(String),
    assigned_sessions   UInt64,
    exposed_sessions    UInt64,
    converted_sessions  UInt64,
    computed_at         DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(computed_at)
PARTITION BY toDate(window_start)
ORDER BY (window_start, experiment_id, variant_id)
TTL toDate(window_start) + INTERVAL 90 DAY
""".strip()


def initialize_schema(client: Any, database: str = "customer_journey") -> list[str]:
    """Create all platform tables idempotently.  Returns the list of DDL strings executed."""
    ddl_statements = [
        build_database_ddl(database),
        build_raw_events_ddl(database),
        build_funnel_metrics_ddl(database),
        build_session_metrics_ddl(database),
        build_revenue_events_ddl(database),
        build_experiment_metrics_ddl(database),
    ]
    for ddl in ddl_statements:
        client.command(ddl)
    return ddl_statements


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
    ingested_at     DateTime64(3, 'UTC') DEFAULT now64(3),
    ingest_date     Date DEFAULT toDate(occurred_at)
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY ingest_date
ORDER BY (event_id)
TTL ingest_date + INTERVAL 90 DAY
""".strip()


def _parse_clickhouse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _event_from_json_line(line: str) -> dict[str, Any]:
    event = json.loads(line)
    event["occurred_at"] = _parse_clickhouse_datetime(event["occurred_at"])
    event["received_at"] = _parse_clickhouse_datetime(event["received_at"])
    return event


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
    replace_existing: bool = False,
) -> int:
    """Create the raw event table and insert JSON Lines events into ClickHouse.

    Set ``replace_existing`` for deterministic local demos where re-running the
    sample loader should refresh, not append to, ``raw_events``.
    """

    client.command(build_raw_events_ddl(database=database))
    if replace_existing:
        client.command(f"TRUNCATE TABLE {database}.raw_events")
    events = [_event_from_json_line(line) for line in lines if line.strip()]
    rows = [_row_from_event(event) for event in events]
    if not rows:
        return 0
    client.insert(
        f"{database}.raw_events",
        rows,
        column_names=RAW_EVENT_COLUMNS,
    )
    return len(rows)


def _normalize_event_datetimes(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for event in events:
        normalized_event = dict(event)
        normalized_event["occurred_at"] = _parse_clickhouse_datetime(event["occurred_at"])
        normalized_event["received_at"] = _parse_clickhouse_datetime(event["received_at"])
        normalized.append(normalized_event)
    return normalized


def _rows_from_dicts(rows: list[dict[str, Any]], columns: list[str]) -> list[tuple[Any, ...]]:
    return [tuple(row.get(column) for column in columns) for row in rows]


def _insert_metric_rows(
    client: Any,
    table: str,
    rows: list[dict[str, Any]],
    columns: list[str],
    database: str,
) -> int:
    if not rows:
        return 0
    client.insert(
        f"{database}.{table}",
        _rows_from_dicts(rows, columns),
        column_names=columns,
    )
    return len(rows)


def insert_sample_analytics_marts(
    client: Any,
    events: list[dict[str, Any]],
    database: str = "customer_journey",
    replace_existing: bool = False,
) -> dict[str, int]:
    """Populate local-demo analytical marts from a finite batch of events.

    The live streaming job owns the raw-event sink. This helper gives the
    deterministic JSONL demo path non-empty API/dashboard tables without claiming
    full continuous mart materialization.
    """

    initialize_schema(client, database=database)
    metric_tables = [
        "funnel_metrics",
        "session_metrics",
        "revenue_events",
        "experiment_metrics",
    ]
    if replace_existing:
        for table in metric_tables:
            client.command(f"TRUNCATE TABLE {database}.{table}")

    events = _normalize_event_datetimes(events)
    counts = {
        "funnel_metrics": _insert_metric_rows(
            client,
            "funnel_metrics",
            compute_funnel_batch(events),
            FUNNEL_METRIC_COLUMNS,
            database,
        ),
        "session_metrics": _insert_metric_rows(
            client,
            "session_metrics",
            compute_session_metrics(events),
            SESSION_METRIC_COLUMNS,
            database,
        ),
        "revenue_events": _insert_metric_rows(
            client,
            "revenue_events",
            compute_revenue_events(events),
            REVENUE_EVENT_COLUMNS,
            database,
        ),
        "experiment_metrics": _insert_metric_rows(
            client,
            "experiment_metrics",
            compute_experiment_batch(events),
            EXPERIMENT_METRIC_COLUMNS,
            database,
        ),
    }
    return counts


def create_client(settings: Settings | None = None) -> Any:
    from clickhouse_connect import get_client

    runtime_settings = settings or Settings()
    return get_client(
        host=runtime_settings.clickhouse_host,
        port=runtime_settings.clickhouse_port,
        database=runtime_settings.clickhouse_database,
        username=runtime_settings.clickhouse_user,
        password=runtime_settings.clickhouse_password,
    )


def load_jsonl_file(
    path: Path,
    settings: Settings | None = None,
    replace_existing: bool = False,
) -> int:
    runtime_settings = settings or Settings()
    client = create_client(runtime_settings)
    lines = path.read_text(encoding="utf-8").splitlines()
    raw_count = insert_raw_events_jsonl(
        client=client,
        lines=lines,
        database=runtime_settings.clickhouse_database,
        replace_existing=replace_existing,
    )
    events = [_event_from_json_line(line) for line in lines if line.strip()]
    insert_sample_analytics_marts(
        client=client,
        events=events,
        database=runtime_settings.clickhouse_database,
        replace_existing=replace_existing,
    )
    return raw_count


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    parser = argparse.ArgumentParser(description="Load journey JSONL into ClickHouse raw_events.")
    parser.add_argument("--input", type=Path, default=Path("data/sample_events.jsonl"))
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Truncate raw_events before loading so local demo reruns are deterministic.",
    )
    args = parser.parse_args()

    count = load_jsonl_file(
        args.input,
        settings=settings,
        replace_existing=args.replace_existing,
    )
    logger.info(
        "loaded customer journey events into clickhouse",
        extra={
            "cji_event_count": count,
            "cji_input_path": str(args.input),
            "cji_database": settings.clickhouse_database,
        },
    )


if __name__ == "__main__":
    main()
