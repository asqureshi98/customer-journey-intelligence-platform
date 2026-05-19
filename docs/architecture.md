# Architecture — Realtime Customer Journey Intelligence Platform

Sprint 0 establishes the local development spine for realtime journey intelligence.

## Overview

The platform is a continuous stream-processing pipeline that ingests synthetic ecommerce
behavioral events, validates and enriches them, applies funnel and session analytics in
micro-batch windows, and materializes results in ClickHouse for sub-second query latency.

The design deliberately avoids a generic "count page views" architecture. Every component
exists to serve a specific analytical capability: funnel collapse detection, revenue
leakage attribution, A/B experiment metric computation, and session quality scoring.

## Data Flow Diagram

```text
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  Local machine — Docker network (journey_net)                               │
  │                                                                             │
  │   Event Generator (Python)                                                  │
  │   ┌────────────────────────┐                                                │
  │   │  JourneySimulator      │  EcommerceEvent objects (Pydantic)             │
  │   │  • 4 behavioral personas│                                               │
  │   │  • 16 event types      │──────────────────────────────────────────┐    │
  │   │  • journey graph       │  confluent-kafka producer                │    │
  │   └────────────────────────┘                                          │    │
  │                                                                        │    │
  │   ┌────────────────────────────────────────────────────────────────────▼─┐ │
  │   │                          Redpanda                                    │ │
  │   │   topic: customer-events     (partitioned by session_id)             │ │
  │   │   topic: customer-events-dlq (bad event quarantine)                  │ │
  │   └─────────────────────────────────┬────────────────────────────────────┘ │
  │                                     │ Kafka source (Spark connector)       │
  │   ┌─────────────────────────────────▼────────────────────────────────────┐ │
  │   │              PySpark Structured Streaming                            │ │
  │   │                                                                      │ │
  │   │  1. Parse JSON  →  2. Pydantic validate  →  3. watermark(occurred_at)│ │
  │   │                          │                         │                 │ │
  │   │                     (invalid)                  (valid)               │ │
  │   │                          │              ┌──────────┴──────────┐      │ │
  │   │                          ▼              │                     │      │ │
  │   │                     DLQ Kafka      funnel windows       session state │ │
  │   │                     topic          (1-min tumbling)   (mapGroupsWith) │ │
  │   │                                         │                     │      │ │
  │   │                               funnel_metrics         session_metrics  │ │
  │   │                                                     revenue_events    │ │
  │   └───────────────────────────────────────────────────────────────────────┘ │
  │                                     │                                      │
  │   ┌─────────────────────────────────▼────────────────────────────────────┐ │
  │   │              ClickHouse (customer_journey DB)                        │ │
  │   │   raw_events / funnel_metrics / session_metrics / revenue_events     │ │
  │   └───────────────────────────────────────────────────────────────────────┘ │
  └─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Event Generator

**Location:** `src/customer_journey_intel/event_generator/`

The generator produces realistic customer journeys rather than random event sequences.

- **Persona model.** Each customer is assigned one of four behavioral archetypes at
  session start: `browser`, `researcher`, `impulse_buyer`, `deal_hunter`. Personas control
  transition probability matrices between event types.
- **Journey graph.** Event sequences are drawn from a directed weighted graph where nodes
  are event types and edge weights are persona-conditional transition probabilities.
- **A/B injection.** A fraction of sessions receive an `experiment_assigned` event near
  the start, followed by `variant_exposed` events aligned with the experiment surface.
- **Signal events.** `page_load_slow` and `api_error_seen` are injected probabilistically
  based on a synthetic "site health" parameter.
- **Faker-backed properties.** Product names, prices, search queries, and shipping
  addresses use Faker for realistic property payloads.

### 2. Redpanda (Kafka-compatible broker)

**Image:** `docker.redpanda.com/redpandadata/redpanda:v24.1.9`

Redpanda is a single binary with no ZooKeeper dependency, starts in under five seconds,
and is fully Kafka API-compatible. The platform uses two topics:

| Topic                    | Purpose                                            |
|--------------------------|----------------------------------------------------|
| `customer-events`        | Primary validated event stream                     |
| `customer-events-dlq`    | Dead-letter queue for schema-invalid events        |

Partitioning strategy: `session_id` as the partition key so all events from a single
session land in the same partition, enabling session-scoped stateful aggregations in
Spark without shuffle overhead.

### 3. PySpark Structured Streaming

**Location:** `src/customer_journey_intel/streaming/`

The Spark job is the core analytical engine performing five processing stages:

1. **Ingest and parse.** Read raw bytes from Redpanda via the Spark Kafka connector.
   Deserialize JSON and apply the `EcommerceEvent` schema projection.

2. **Schema validation and DLQ routing.** A Spark UDF wraps Pydantic validation. Events
   that fail validation are written to the DLQ topic with a structured error envelope;
   valid events continue downstream.

3. **Watermark and window assignment.** A 10-minute watermark on `occurred_at` handles
   late-arriving mobile events, correctly placing them into their original time windows.

4. **Funnel and session aggregation.** Two parallel streaming branches:
   - Tumbling 1-minute windows compute per-event-type counts and conversion rates for
     the `funnel_metrics` table.
   - Session-keyed state using `mapGroupsWithState` tracks each session through funnel
     stages and emits `session_metrics` records on session timeout.

5. **Revenue leakage detection.** A stateful processor monitors `payment_attempted`
   events. Sessions without a matching `payment_succeeded` within 5 minutes generate a
   leakage record in `revenue_events`.

**Sprint 0 scope:** The streaming sink is intentionally lightweight console output. This
keeps unit tests fast and avoids requiring Docker for CI. The next sprint adds ClickHouse
table DDL and a `foreachBatch` writer.

### 4. ClickHouse (Real-time Analytics Warehouse)

**Image:** `clickhouse/clickhouse-server:24.3`

ClickHouse stores enriched analytics outputs. Its columnar storage and vectorized query
engine support the time-series aggregations and funnel queries that executive dashboards
require.

| Table             | Engine                         | Primary use                          |
|-------------------|--------------------------------|--------------------------------------|
| `raw_events`      | MergeTree (partitioned by day) | Full audit trail, ad-hoc exploration |
| `funnel_metrics`  | AggregatingMergeTree           | Funnel conversion rates per window   |
| `session_metrics` | ReplacingMergeTree             | Per-session KPIs, updated on timeout |
| `revenue_events`  | MergeTree                      | Payment outcomes and leakage alerts  |

## Late-Arriving Event Handling Strategy

Mobile apps and single-page applications often buffer events locally and flush them in
batches when connectivity is restored. Without special handling, late events would corrupt
time-window aggregates.

**Strategy:** A Spark event-time watermark of **10 minutes** is declared on `occurred_at`.
Spark tracks the maximum observed `occurred_at` across all partitions. Any event whose
`occurred_at` is older than `(max_observed - 10 min)` is dropped. Events within the
watermark are correctly assigned to their original time windows.

For events that exceed the watermark, the DLQ envelope records the late-arrival delta so
data quality dashboards can track the volume of dropped late events over time.

## Bad Event Quarantine (DLQ)

Events that fail Pydantic schema validation are routed to `customer-events-dlq` with a
structured error envelope:

```json
{
  "original_payload": "<raw JSON string>",
  "error_type": "schema_validation_error",
  "error_detail": "event_name: value is not a valid enumeration member",
  "received_at": "2026-01-01T12:00:05Z",
  "kafka_partition": 3,
  "kafka_offset": 10042
}
```

The DLQ topic can be replayed after schema fixes. The DLQ record count feeds a Prometheus
counter `journey_intel_dlq_events_total` in the optional observability profile.

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

The Spark stateful processor stores the highest funnel stage reached per session. On
session timeout (30-minute inactivity), a `session_metrics` record is emitted with:
- `max_funnel_stage`: the deepest stage reached
- `funnel_collapse`: true if the session reached checkout but did not convert
- `cart_value_at_abandon`: estimated revenue opportunity lost

## Revenue Leakage Detection Approach

Revenue leakage is a `payment_attempted` event not followed by `payment_succeeded` within
the same session within a 5-minute window.

Detection logic:
1. A `payment_attempted` event opens a leakage candidate record keyed on `session_id`.
2. The record stores `attempted_at`, `cart_value`, `payment_method`, and any active
   experiment variant.
3. If `payment_succeeded` arrives within 5 minutes, the record is closed as resolved.
4. If the session times out without a success, the record is written to `revenue_events`
   with `leakage=true` and `resolution=unresolved`.

This enables real-time alerting and post-hoc attribution analysis by experiment variant,
payment method, and device type.

## Implementation Milestones

| Sprint | Milestone                                                              |
|--------|------------------------------------------------------------------------|
| 0      | Repo scaffold, Pydantic contracts, simulator, CI pipeline (done)       |
| 1      | ClickHouse DDL, foreachBatch sink, Redpanda producer CLI               |
| 2      | Stateful session processor, funnel collapse detection                  |
| 3      | Revenue leakage detector, A/B experiment metrics                       |
| 4      | DLQ quarantine pipeline, late-event watermark hardening                |
| 5      | MinIO Parquet lake, dbt-clickhouse models, Superset dashboards         |
| 6      | Prometheus/Grafana observability, Airflow orchestration                |
