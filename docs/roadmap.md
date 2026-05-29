# Roadmap and implementation status

This page keeps the project honest for portfolio review. It separates implemented work from partial foundations and future production work.

## Implemented

- Pydantic `EcommerceEvent` contract with stable identity/session/journey fields.
- Deterministic synthetic ecommerce journey generator and JSONL CLI.
- Redpanda producer for `customer-events`.
- Docker Compose stack for Redpanda, Redpanda Console, and ClickHouse.
- PySpark Structured Streaming Kafka read, raw JSON preservation, projection, invalid-row split, 10-minute watermark, and `event_id` dedupe.
- Checkpointed Spark `foreachBatch` sink to ClickHouse `raw_events`.
- Direct JSONL ClickHouse sample loader.
- ClickHouse init SQL for `raw_events`, `funnel_metrics`, `session_metrics`, `revenue_events`, and `experiment_metrics`.
- Pure-Python aggregate helpers for funnel, session, revenue, and experiment rows.
- FastAPI app with `/health`, `/funnel`, `/sessions`, `/revenue-leakage`, and `/experiments`.
- Optional Streamlit dashboard with API-backed or fallback demo data.
- Data-quality validators and tests for event semantics, metrics, dedupe, DLQ envelopes, schema, API, dashboard, and operations.
- Structured logging, readiness script, Compose healthchecks, and CI-friendly `make check`.

## Partially implemented

| Capability | What exists | Remaining work |
|---|---|---|
| DLQ pipeline | Topic creation, invalid-row split, envelope helper, tests | Publish invalid Spark rows to `customer-events-dlq`, replay tooling, quality counters |
| Analytical marts | ClickHouse DDL, helper functions, API repository queries | Continuous Spark writers to populate metric tables from streaming batches |
| Revenue leakage | Revenue-event extraction and API/dashboard story | Stateful payment-attempt windowing and alert rules |
| Experiment analytics | Experiment metric model/helper/API/dashboard story | Full assignment/exposure/conversion attribution in streaming marts |
| Dashboard assets | Streamlit app and capture instructions | Committed screenshots or hosted demo environment, if desired |

## Near-term next milestones

1. Wire Spark invalid-row batches to a Redpanda DLQ producer.
2. Add Spark `foreachBatch` metric writers for funnel/session/revenue/experiment tables.
3. Add replay-safe backfill commands for aggregate marts from `raw_events`.
4. Add a small dashboard screenshot set under `docs/assets/dashboard/` generated from local sample data.
5. Add CI job variants for optional Docker-backed integration tests when runners support Compose.

## Longer-term production ideas

- Object storage lake for Parquet history.
- dbt-clickhouse transformations for documented analytical marts.
- Superset or another BI layer for governed dashboards.
- Airflow or Dagster orchestration for batch backfills and replay jobs.
- Prometheus/Grafana for metrics and alerting.
- Great Expectations or Soda checks for data-quality observability.
- Schema registry compatibility and versioned event migrations.

These are roadmap ideas, not claims about the current local implementation.
