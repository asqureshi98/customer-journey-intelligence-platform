"""Tests for the ClickHouse foreachBatch sink helpers.

All tests run without Docker or a live Spark session.  Spark Row objects are
simulated with a simple namespace class.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from customer_journey_intel.streaming.sink import (
    RAW_EVENTS_SINK_COLUMNS,
    checkpoint_location_options,
    make_foreachbatch_sink,
    row_from_spark_row,
    rows_from_batch,
    write_batch_to_clickhouse,
)


def _make_row(**kwargs) -> SimpleNamespace:
    """Create a fake Spark Row as a SimpleNamespace."""
    defaults = {
        "event_id": "evt-001",
        "event_name": "product_viewed",
        "occurred_at": datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC),
        "received_at": datetime(2026, 3, 1, 10, 0, 2, tzinfo=UTC),
        "customer_id": "cust_001",
        "anonymous_id": None,
        "session_id": "sess_abc",
        "journey_stage": "consideration",
        "channel": "web",
        "experiment_id": None,
        "variant_id": None,
        "properties": {"product_id": "sku_1"},
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class FakeCHClient:
    def __init__(self):
        self.inserted: list[dict] = []

    def insert(self, table, data, column_names):
        self.inserted.append({"table": table, "data": data, "column_names": column_names})


# ── row_from_spark_row ────────────────────────────────────────────────────────


def test_row_from_spark_row_converts_dict_properties_to_json():
    row = _make_row(properties={"price": "9.99", "currency": "USD"})
    result = row_from_spark_row(row)
    assert isinstance(result[-1], str)
    assert '"currency"' in result[-1]
    assert '"price"' in result[-1]


def test_row_from_spark_row_handles_none_properties():
    row = _make_row(properties=None)
    result = row_from_spark_row(row)
    assert result[-1] == "{}"


def test_row_from_spark_row_passthrough_string_properties():
    row = _make_row(properties='{"already": "json"}')
    result = row_from_spark_row(row)
    assert result[-1] == '{"already": "json"}'


def test_row_from_spark_row_tuple_length_matches_columns():
    row = _make_row()
    result = row_from_spark_row(row)
    assert len(result) == len(RAW_EVENTS_SINK_COLUMNS)


def test_row_from_spark_row_first_field_is_event_id():
    row = _make_row(event_id="unique-id-xyz")
    result = row_from_spark_row(row)
    assert result[0] == "unique-id-xyz"


# ── rows_from_batch ───────────────────────────────────────────────────────────


def test_rows_from_batch_converts_multiple_rows():
    batch = [_make_row(event_id=f"evt-{i}") for i in range(3)]
    result = rows_from_batch(batch)
    assert len(result) == 3
    assert result[0][0] == "evt-0"
    assert result[2][0] == "evt-2"


def test_rows_from_batch_empty_returns_empty_list():
    assert rows_from_batch([]) == []


# ── write_batch_to_clickhouse ─────────────────────────────────────────────────


def test_write_batch_to_clickhouse_calls_insert_with_correct_args():
    client = FakeCHClient()
    rows = [row_from_spark_row(_make_row())]
    count = write_batch_to_clickhouse(client, rows, database="test_db")
    assert count == 1
    assert client.inserted[0]["table"] == "test_db.raw_events"
    assert client.inserted[0]["column_names"] == RAW_EVENTS_SINK_COLUMNS


def test_write_batch_to_clickhouse_empty_batch_skips_insert():
    client = FakeCHClient()
    count = write_batch_to_clickhouse(client, [], database="test_db")
    assert count == 0
    assert client.inserted == []


def test_write_batch_to_clickhouse_returns_row_count():
    client = FakeCHClient()
    rows = [row_from_spark_row(_make_row(event_id=f"e{i}")) for i in range(5)]
    assert write_batch_to_clickhouse(client, rows) == 5


# ── checkpoint_location_options ───────────────────────────────────────────────


def test_checkpoint_location_options_returns_dict_with_location():
    opts = checkpoint_location_options("/tmp/my-checkpoint")
    assert opts == {"checkpointLocation": "/tmp/my-checkpoint"}


# ── make_foreachbatch_sink ────────────────────────────────────────────────────


def test_make_foreachbatch_sink_writes_valid_batch():
    client = FakeCHClient()
    sink = make_foreachbatch_sink(client_factory=lambda: client, database="cj")

    class FakeBatchDF:
        def collect(self):
            return [_make_row()]

    sink(FakeBatchDF(), batch_id=0)
    assert len(client.inserted) == 1
    assert client.inserted[0]["table"] == "cj.raw_events"


def test_make_foreachbatch_sink_skips_empty_batch():
    client = FakeCHClient()
    sink = make_foreachbatch_sink(client_factory=lambda: client, database="cj")

    class EmptyBatchDF:
        def collect(self):
            return []

    sink(EmptyBatchDF(), batch_id=0)
    assert client.inserted == []
