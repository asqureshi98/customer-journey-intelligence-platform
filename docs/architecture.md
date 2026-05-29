# Architecture — Realtime Customer Journey Intelligence Platform

The current local implementation establishes a portfolio-ready spine for realtime journey intelligence: synthetic ecommerce events, Redpanda publishing, Spark Kafka parsing, event-time deduplication, checkpointed ClickHouse raw-event writes, ClickHouse analytical schemas, aggregate helper logic, FastAPI endpoints, and an optional Streamlit dashboard. It keeps the remaining production gaps explicit.

## Overview

The target platform is a continuous stream-processing pipeline for synthetic ecommerce behavioral events. The current implementation includes event generation, Redpanda publishing, Spark Kafka parsing, event-time deduplication, checkpointed ClickHouse raw-event writes, ClickHouse schema initialization, a direct JSONL loader, pure-Python aggregate helpers, demo API queries, and a dashboard. Continuous Spark aggregate writers and live DLQ publication are planned next.

The design deliberately avoids a generic "count page views" architecture. Every component
exists to serve a specific analytical capability: funnel collapse detection, revenue
leakage attribution, A/B experiment metric computation, and session quality scoring.

## Data Flow Diagram

```text
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  Local machine — Docker Compose project network                             │
  │                                                                             │
  │   Event Generator (Python)                                                  │
  │   ┌────────────────────────┐                                                │
  │   │  JourneySimulator      │  EcommerceEvent objects (Pydantic)             │
  │   │  • deterministic seed │                                               │
  │   │  • core event path     │──────────────────────────────────────────┐    │
  │   │  • JSONL rendering     │  confluent-kafka producer                │    │
  │   └────────────────────────┘                                          │    │
  │                                                                        │    │
  │   ┌────────────────────────────────────────────────────────────────────▼─┐ │
  │   │                          Redpanda                                    │ │
  │   │   topic: customer-events     (partitioned by session_id)             │ │
  │   │   topic: customer-events-dlq (created; live publish still planned)       │ │
  │   └─────────────────────────────────┬────────────────────────────────────┘ │
  │                                     │ Kafka source (Spark connector)       │
  │   ┌─────────────────────────────────▼────────────────────────────────────┐ │
  │   │              PySpark Structured Streaming                            │ │
  │   │                                                                      │ │
  │   │  Current: parse JSON, keep invalid rows separate, dedupe by event_id,   │ │
  │   │           and write valid raw events to console or ClickHouse          │ │
  │   │  Planned: live DLQ topic publishing, funnel windows, stateful session  │ │
  │   │           metrics, and revenue leakage aggregate writers               │ │
  │   └───────────────────────────────────────────────────────────────────────┘ │
  │                                     │                                      │
  │   ┌─────────────────────────────────▼────────────────────────────────────┐ │
  │   │              ClickHouse (customer_journey DB)                        │ │
  │   │   current: raw_events + schema-created metric tables                  │ │
  │   └───────────────────────────────────────────────────────────────────────┘ │
  └─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Event Generator

**Location:** `src/customer_journey_intel/event_generator/`

The generator currently produces deterministic, ordered ecommerce journeys with a landing event, discovery/search, product view, cart, and probabilistic checkout/payment outcome. It emits Pydantic `EcommerceEvent` objects and JSON Lines for local seeding. Rich personas, experiment injection, reliability friction events, and Faker-backed payloads are planned enhancements, not current behavior.

### 2. Redpanda (Kafka-compatible broker)

**Image:** `docker.redpanda.com/redpandadata/redpanda:v24.1.9`

Redpanda is a single binary with no ZooKeeper dependency and is Kafka API-compatible. The current producer and Spark reader use the primary topic; `make create-topics` also creates a DLQ topic for the next live quarantine step:

| Topic                    | Purpose                                            |
|--------------------------|----------------------------------------------------|
| `customer-events`        | Primary validated event stream                     |
| `customer-events-dlq`    | DLQ topic created locally; live Spark publishing is not wired yet |

Partitioning strategy: `session_id` as the partition key so all events from a single
session land in the same partition, enabling session-scoped stateful aggregations in
Spark without shuffle overhead.

### 3. PySpark Structured Streaming

**Location:** `src/customer_journey_intel/streaming/`

The Spark job is the planned analytical engine. Current and planned stages are:

1. **Implemented ingest, parse, and projection.** Read raw bytes from Redpanda via the Spark Kafka connector, preserve the raw JSON string, deserialize JSON, and project the `EcommerceEvent` fields.

2. **Implemented valid/invalid split and DLQ envelope helpers.** Rows that fail JSON parsing or lack `event_id` are separated from the valid stream. Pure Python helpers create serializable DLQ envelopes for quarantine tests; live Kafka DLQ publishing remains a documented follow-up.

3. **Implemented watermark and duplicate handling.** Valid events use a 10-minute event-time watermark on `occurred_at` and `dropDuplicates(["event_id"])` before writes.

4. **Implemented raw ClickHouse sink.** `--sink clickhouse` uses `foreachBatch` and a configurable checkpoint directory to insert valid raw events into `customer_journey.raw_events`.

5. **Planned aggregate writers.** Funnel, session, revenue, and experiment metric schemas exist in ClickHouse, but streaming branches that populate those tables are not implemented yet.

**Current scope:** The streaming job reads from Redpanda, deduplicates valid events by `event_id`, and can either print them (`make stream-local`) or write them to ClickHouse raw storage (`make stream-clickhouse`). A separate ClickHouse JSONL loader remains available for deterministic local demos without running Spark continuously.

### 4. ClickHouse (Real-time Analytics Warehouse)

**Image:** `clickhouse/clickhouse-server:24.3`

ClickHouse currently stores raw generated events loaded either by the Spark `foreachBatch` sink or by the JSONL demo loader. Docker init SQL creates `raw_events` plus metric tables so local development can start with the full schema even before all aggregate writers exist.

| Table             | Engine                         | Primary use                          |
|-------------------|--------------------------------|--------------------------------------|
| `raw_events`      | ReplacingMergeTree by event_id | Full audit trail, idempotent raw sink |
| `funnel_metrics`  | ReplacingMergeTree             | Schema ready; writer planned         |
| `session_metrics` | ReplacingMergeTree             | Schema ready; writer planned         |
| `revenue_events`  | ReplacingMergeTree             | Schema ready; writer planned         |
| `experiment_metrics` | ReplacingMergeTree          | Schema ready; writer planned         |

## Late-Arriving Event Handling Strategy

Mobile apps and single-page applications often buffer events locally and flush them in
batches when connectivity is restored. Without special handling, late events would corrupt
time-window aggregates.

**Implemented foundation:** The Spark stream declares a 10-minute watermark on `occurred_at` before `dropDuplicates(["event_id"])`, which bounds duplicate state and prepares the raw sink for late arrivals within that horizon. Aggregate windows that drop data beyond the watermark are not implemented yet.

Planned extension: late-event DLQ envelopes can include the late-arrival delta so data quality dashboards can track dropped-late volume over time.

## Bad Event Quarantine (DLQ)

Implemented foundation: events that fail Spark JSON parsing or do not contain `event_id` are split into an invalid stream, and `src/customer_journey_intel/streaming/dlq.py` provides a tested envelope shape for quarantine:

```json
{
  "event_id": "<original event_id or generated UUID>",
  "raw_payload": "<raw JSON string>",
  "error_type": "parse_error",
  "error_message": "event.event_id is missing",
  "received_at": "2026-01-01T12:00:05Z",
  "dlq_enqueued_at": "2026-01-01T12:00:06Z"
}
```

The live Spark job currently prints invalid rows for visibility. Publishing serialized envelopes to `customer-events-dlq` from a `foreachBatch` producer is the remaining live sink step. In the planned production path, the DLQ topic can be replayed after schema fixes. Observability counters are not implemented in the current scaffold.

## Funnel Analytics Approach

The funnel is modeled as a five-stage ordered sequence per session:

```
acquisition → discovery → intent → checkout → payment → conversion
```

Stage membership rules:
- **acquisition**: `homepage_viewed`
- **discovery**: `search_performed`, `category_viewed`, `product_viewed`
- **intent**: `add_to_cart` (entering), `remove_from_cart` (hesitation signal)
- **checkout**: `checkout_started`, `shipping_info_added`
- **payment**: `payment_attempted`
- **conversion**: `payment_succeeded` + `order_completed`

Planned Spark stateful processing will store the highest funnel stage reached per session. On
session timeout (30-minute inactivity), a `session_metrics` record will be emitted with:
- `max_funnel_stage`: the deepest stage reached
- `funnel_collapse`: true if the session reached checkout but did not convert
- `cart_value_at_abandon`: estimated revenue opportunity lost

## Revenue Leakage Detection Approach

Planned revenue leakage detection treats a `payment_attempted` event not followed by `payment_succeeded` in the same session within a 5-minute window as leakage.

Detection logic:
1. A `payment_attempted` event opens a leakage candidate record keyed on `session_id`.
2. The record stores `attempted_at`, `cart_value`, `payment_method`, and any active
   experiment variant.
3. If `payment_succeeded` arrives within 5 minutes, the record is closed as resolved.
4. If the session times out without a success, the record is written to `revenue_events`
   with `leakage=true` and `resolution=unresolved`.

This will enable real-time alerting and post-hoc attribution analysis by experiment variant, payment method, and device type once the planned processor is implemented.

## Implementation status

| Capability | Status |
|------------|--------|
| Repo scaffold, contracts, simulator, CI-friendly tests | Implemented |
| Redpanda producer CLI, stream-local command, ClickHouse raw loader, demo API | Implemented |
| Spark `foreachBatch` ClickHouse raw sink, watermarking, and dedupe | Implemented |
| ClickHouse analytical schemas and pure-Python aggregate helpers | Implemented foundation; continuous Spark writers planned |
| FastAPI and optional Streamlit dashboard | Implemented for local portfolio demos |
| DLQ quarantine | Envelope helpers and topic creation implemented; live Spark publishing planned |
| Production lake, dbt models, external BI, orchestration, and monitoring | Roadmap |

See `roadmap.md` for the fuller implemented/partial/planned matrix.
