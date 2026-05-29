"""ClickHouse foreachBatch sink helpers for Spark Structured Streaming.

All public functions in this module are pure (no I/O) except
``make_foreachbatch_sink``, which returns a closure.  Unit tests can exercise
``row_from_spark_row``, ``rows_from_batch``, ``write_batch_to_clickhouse``, and
``checkpoint_location_options`` without a live Spark or ClickHouse process.

Live wiring:
    sink_fn = make_foreachbatch_sink(
        client_factory=lambda: create_client(settings),
        database=settings.clickhouse_database,
    )
    query = (
        valid_df.writeStream
        .outputMode("append")
        .foreachBatch(sink_fn)
        .options(**checkpoint_location_options("/tmp/cji-checkpoint"))
        .start()
    )
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

RAW_EVENTS_SINK_COLUMNS = [
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


def row_from_spark_row(row: Any) -> tuple[Any, ...]:
    """Convert a Spark Row (or any attribute-accessible object) to a ClickHouse tuple.

    Properties are serialised to JSON if they arrive as a dict (Spark MapType);
    if already a string, they are passed through unchanged.
    """
    props = row.properties
    if isinstance(props, dict):
        props_json = json.dumps(props, sort_keys=True)
    elif props is None:
        props_json = "{}"
    else:
        props_json = str(props)

    return (
        str(row.event_id) if row.event_id else "",
        str(row.event_name) if row.event_name else "",
        row.occurred_at,
        row.received_at,
        row.customer_id,
        row.anonymous_id,
        str(row.session_id) if row.session_id else "",
        str(row.journey_stage) if row.journey_stage else "",
        str(row.channel) if row.channel else "",
        row.experiment_id,
        row.variant_id,
        props_json,
    )


def rows_from_batch(collected_rows: list[Any]) -> list[tuple[Any, ...]]:
    """Convert a list of Spark Rows to ClickHouse insert tuples."""
    return [row_from_spark_row(r) for r in collected_rows]


def write_batch_to_clickhouse(
    client: Any,
    rows: list[tuple[Any, ...]],
    database: str = "customer_journey",
    table: str = "raw_events",
) -> int:
    """Insert pre-converted row tuples into a ClickHouse table.

    Returns the number of rows inserted, or 0 for an empty batch.
    """
    if not rows:
        return 0
    client.insert(
        f"{database}.{table}",
        rows,
        column_names=RAW_EVENTS_SINK_COLUMNS,
    )
    return len(rows)


def checkpoint_location_options(path: str) -> dict[str, str]:
    """Return the Spark writeStream option dict that enables checkpointing."""
    return {"checkpointLocation": path}


def make_foreachbatch_sink(
    client_factory: Callable[[], Any],
    database: str = "customer_journey",
) -> Callable[[Any, int], None]:
    """Return a ``foreachBatch`` callable that writes micro-batches to ClickHouse.

    The ClickHouse client is created fresh per batch via ``client_factory`` so
    that the closure remains serialisable by Spark.  For high-throughput
    deployments replace ``client_factory`` with a thread-local pool.
    """

    def _sink(batch_df: Any, batch_id: int) -> None:  # noqa: ARG001
        collected = batch_df.collect()
        rows = rows_from_batch(collected)
        if not rows:
            return
        client = client_factory()
        write_batch_to_clickhouse(client, rows, database=database)

    return _sink
