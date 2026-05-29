# Realtime Customer Journey Intelligence Platform

A production-inspired portfolio project for turning ecommerce behavior streams into customer journey intelligence: funnel drop-off, checkout risk, revenue leakage, A/B experiment readouts, and executive dashboard slices. The repository is built to show how a small local data platform can move from event contracts and streaming ingestion to reviewer-friendly analytics surfaces without depending on paid cloud services.

This is intentionally not a generic clickstream tutorial. The domain model is organized around real commerce questions: where shoppers lose intent, which payment failures put revenue at risk, how experiment variants perform, and how operators can trust the data path from generated events through Redpanda, Spark, ClickHouse, FastAPI, and an optional Streamlit dashboard.

![Platform architecture](docs/assets/architecture.svg)

## What the project demonstrates

- Synthetic but realistic customer journey event generation with stable identities, sessions, funnel stages, payment outcomes, experiment attributes, and reliability/friction events.
- Pydantic event contracts and data-quality validators that reject incompatible stages, invalid timestamps, missing payment metadata, and negative monetary fields.
- Redpanda publishing plus a PySpark Structured Streaming job that reads Kafka-compatible events, parses JSON, separates invalid rows, watermarks event time, deduplicates by `event_id`, and writes valid raw events to ClickHouse with checkpointed `foreachBatch`.
- ClickHouse schemas for raw events and analytical marts (`funnel_metrics`, `session_metrics`, `revenue_events`, `experiment_metrics`), with pure-Python aggregate helpers and tested repository queries for the API layer.
- FastAPI endpoints and an optional Streamlit dashboard for portfolio demos of funnel, session, revenue leakage, and experiment analytics.
- Local operational hardening: Docker Compose healthchecks, readiness scripts, structured logging, `.env.example`, and CI-friendly test/lint commands.

## Current implementation status

| Area | Status | Notes |
|---|---|---|
| Event contracts and simulator | Implemented | Pydantic `EcommerceEvent`, deterministic generator, JSONL rendering. |
| Redpanda publishing | Implemented | `make publish-sample` publishes JSONL to `customer-events`. |
| Spark streaming ingest | Implemented | Kafka read, parse/project, invalid split, 10-minute watermark, `event_id` dedupe. |
| ClickHouse raw sink | Implemented | Checkpointed Spark `foreachBatch` sink and direct JSONL sample loader. |
| Analytical marts | Partially implemented | ClickHouse tables, pure-Python aggregate helpers, and API query layer exist; continuous Spark writers into metric tables remain planned. |
| DLQ | Partially implemented | DLQ topic creation and tested envelope helpers exist; live Spark publishing to `customer-events-dlq` remains planned. |
| API and dashboard | Implemented for local demo | FastAPI endpoints and optional Streamlit app run locally; dashboard can use API data or deterministic fallback data. |
| Production deployment | Roadmap | No cloud services, orchestration platform, external monitoring stack, or committed screenshots. |

## MVP stack

- PySpark Structured Streaming for stream processing
- Redpanda as the Kafka-compatible event broker
- ClickHouse as the real-time analytics warehouse
- Pydantic data contracts for event validation
- FastAPI for analytics endpoints
- Optional Streamlit for a visual portfolio dashboard
- Docker Compose for local infrastructure
- pytest and ruff for test and quality gates

## Repository layout

```text
src/customer_journey_intel/
  api/                    FastAPI app, Pydantic response models, ClickHouse queries
  common/                 Settings and structured logging
  contracts/              Event contracts and data-quality validators
  dashboard/              Optional Streamlit portfolio dashboard
  event_generator/        Synthetic journey simulator, JSONL CLI, Redpanda producer
  storage/                ClickHouse DDL/loader helpers
  streaming/              PySpark job, raw sink, dedupe, DLQ, aggregate helpers
tests/                    Unit/integration tests designed to run without paid services
docs/                     Architecture, runbooks, data quality, case study, roadmap
docs/assets/              GitHub-renderable SVG diagrams
docker-compose.yml        Canonical local Redpanda, Console, and ClickHouse stack
infrastructure/           Service notes and ClickHouse init SQL
```

## Quick start

```bash
make setup
make check
make generate-sample
```

`make check` runs ruff format check, ruff lint, and pytest. `make generate-sample` writes JSON Lines events to `data/sample_events.jsonl`.

For the optional dashboard:

```bash
make setup-dashboard
make dashboard-local
```

For the local infrastructure path:

```bash
make docker-up
make wait-services
make create-topics
make generate-sample
make publish-sample
```

## Local demo commands

```bash
# No-Docker smoke path: generate events and run tests
make smoke-local

# Start Redpanda, Redpanda Console, and ClickHouse
make docker-up
make wait-services
make create-topics

# Run the PySpark Kafka reader with console output
make stream-local

# Or run the checkpointed Spark -> ClickHouse raw sink in one terminal,
# then publish generated events from another terminal
make stream-clickhouse
make publish-sample

# Load sample JSONL directly into ClickHouse for deterministic API/dashboard exploration
make load-clickhouse-sample

# Serve portfolio analytics endpoints on http://127.0.0.1:8000
make api-local

# Serve the optional Streamlit dashboard on http://localhost:8501
make setup-dashboard
make dashboard-local

# Point dashboard aggregate panels at the local API when available
CJI_API_BASE_URL=http://127.0.0.1:8000 make dashboard-local
```

## API surfaces

The local FastAPI service exposes:

- `GET /health`
- `GET /funnel`
- `GET /sessions`
- `GET /revenue-leakage`
- `GET /experiments`

Example response shapes:

```json
{
  "funnel": [{"journey_stage": "checkout", "event_name": "checkout_started", "event_count": 42, "sessions": 38, "conversion_rate": 0.62}],
  "revenue_leakage": [{"failure_reason": "issuer_declined", "failed_payments": 7, "at_risk_revenue": 932.41, "affected_sessions": 7}],
  "experiments": [{"experiment_id": "checkout_cta", "variant_id": "variant_b", "assigned_sessions": 120, "exposed_sessions": 114, "converted_sessions": 31, "conversion_rate": 0.27}]
}
```

Values above are illustrative; local results depend on the generated sample data and whether the API is backed by ClickHouse or the dashboard fallback dataset.

## Documentation map

Start with `docs/index.md` for the complete reviewer guide.

- `docs/pipeline_design.md` — implemented pipeline, data flow, and analytical model.
- `docs/data_quality.md` — event contracts, DLQ strategy, dedupe, and current validation coverage.
- `docs/operational_runbook.md` — local startup, health checks, smoke paths, and troubleshooting.
- `docs/portfolio_case_study.md` — recruiter/reviewer narrative, business questions, and sample outputs.
- `docs/roadmap.md` — honest implemented/partial/planned matrix and next milestones.
- `docs/dashboard.md` — optional Streamlit dashboard walkthrough.
- `docs/data_model.md` — event taxonomy and ClickHouse schema reference.
- `docs/demo_script.md` — step-by-step local demo script.

## Local services

- Redpanda broker: `localhost:19092`
- Redpanda console: `http://localhost:8080`
- ClickHouse HTTP: `http://localhost:8123`
- ClickHouse native: `localhost:9000`
- FastAPI: `http://127.0.0.1:8000`
- Streamlit dashboard: `http://localhost:8501`

## Notes

No secrets are stored in the repository. Use `.env.example` as the local configuration template. The project is designed for local portfolio demonstration and CI-friendly verification; it does not claim production deployment, cloud hosting, or real customer data ingestion.
