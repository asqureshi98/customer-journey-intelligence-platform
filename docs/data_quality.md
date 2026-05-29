# Data quality and trust boundaries

The project treats data quality as part of the pipeline, not an afterthought. The current implementation validates event shape, rejects incompatible business semantics, preserves raw payloads for rejected records, and tests dedupe and warehouse contract behavior.

## Implemented contract checks

The Pydantic event contract and data-quality helpers cover:

- At least one identity: `customer_id` or `anonymous_id`.
- Known event names and journey stages.
- Compatible event-name-to-stage combinations.
- `received_at` not preceding `occurred_at`.
- Non-negative monetary properties such as `cart_value`, `amount`, and `revenue`.
- Experiment events carrying both `experiment_id` and `variant_id`.
- Payment events carrying payment-method context.
- Session metrics where `first_seen` is not after `last_seen`.
- Revenue/session metrics with non-negative monetary values.

## Streaming quality controls

- Raw JSON is preserved before parsing so invalid records can be diagnosed.
- Spark splits valid and invalid rows before writing valid records.
- A 10-minute event-time watermark on `occurred_at` prepares the stream for bounded late-arrival handling.
- `dropDuplicates(["event_id"])` prevents replayed events from duplicating the raw sink.
- ClickHouse `raw_events` uses `ReplacingMergeTree(ingested_at)` keyed by `event_id` for idempotent local replays.

## DLQ status

Implemented:

- `customer-events-dlq` topic creation via `make create-topics`.
- Tested DLQ envelope helpers in `src/customer_journey_intel/streaming/dlq.py`.
- Invalid rows separated by the Spark job and printed for visibility.

Planned:

- A Spark `foreachBatch` producer that serializes invalid rows and publishes them to `customer-events-dlq`.
- Replay tooling for corrected DLQ records.
- Data-quality counters exposed to an observability backend.

Example envelope shape:

```json
{
  "envelope_id": "018f4dd7-9a18-7c7a-b201-1f6d26cdd999",
  "event_id": "018f4dd7-9a18-7c7a-b201-1f6d26cdd001",
  "raw_payload": "{...}",
  "error_type": "validation_error",
  "error_message": "event.event_id is missing",
  "received_at": "2026-01-01T12:00:05Z",
  "dlq_enqueued_at": "2026-01-01T12:00:06Z"
}
```

## Test coverage map

| Coverage area | Test file |
|---|---|
| Event contract identity and stage validation | `tests/test_event_contracts.py` |
| Generator journey order and JSONL rendering | `tests/test_event_generator.py` |
| Data-quality rules for event/session/revenue semantics | `tests/test_data_quality.py` |
| Dedupe helpers | `tests/test_dedupe.py` |
| DLQ envelope creation and serialization | `tests/test_dlq.py` |
| ClickHouse DDL and storage insert behavior | `tests/test_clickhouse_schema.py`, `tests/test_clickhouse_storage.py` |
| Streaming projection and sink helpers | `tests/test_streaming_job.py`, `tests/test_streaming_sink.py` |
| API repository queries and endpoint response models | `tests/test_analytics_repository.py`, `tests/test_api_app.py` |
| Dashboard fallback/sample-data loading | `tests/test_dashboard.py` |
| Operational readiness and healthcheck config | `tests/test_operational_hardening.py` |

## Why this matters for a portfolio review

The docs and dashboard can tell a strong story only if the pipeline is honest about data trust. This project therefore documents which guarantees are real today and which controls are still roadmap work, avoiding overclaiming production readiness.
