# Realtime Customer Journey Intelligence Platform

Sprint 0 scaffold for an ecommerce journey intelligence platform. The project turns synthetic customer behavior streams into real-time funnel analytics, revenue leakage signals, and executive-ready journey metrics.

This is intentionally not a generic clickstream tutorial. The domain model is framed around customer journeys: acquisition, discovery, consideration, cart, checkout, payment, retention, experiment exposure, and reliability friction.

## MVP stack

- PySpark Structured Streaming for stream processing
- Redpanda as the Kafka-compatible event broker
- ClickHouse as the real-time analytics warehouse
- Pydantic data contracts for event validation
- Docker Compose for local infrastructure
- pytest and ruff for test and quality gates

## Repository layout

```text
src/customer_journey_intel/
  common/                 Shared settings and constants
  contracts/              Pydantic ecommerce event contracts
  event_generator/        Synthetic journey simulator and JSONL CLI
  streaming/              PySpark Structured Streaming starter job
tests/                    Unit tests that do not require Docker
docs/                     Architecture and data model notes
docker-compose.yml        Local Redpanda and ClickHouse service stack
infrastructure/           Additional infrastructure notes and compose skeleton
```

## Quick start

```bash
make setup
make test
make lint
make generate-sample
make docker-up
```

`make generate-sample` writes JSON Lines events to `data/sample_events.jsonl`. `make docker-up` starts Redpanda and ClickHouse for local integration work.

## Local services

- Redpanda broker: `localhost:19092`
- Redpanda console: `http://localhost:8080`
- ClickHouse HTTP: `http://localhost:8123`
- ClickHouse native: `localhost:9000`

## Event contract summary

Every event carries stable journey context:

- `event_id`, `event_name`, `occurred_at`, `received_at`
- `customer_id` or `anonymous_id`
- `session_id`, `journey_stage`, `channel`
- flexible `properties` for product, order, experiment, payment, and reliability details

See `docs/data_model.md` for the Sprint 0 taxonomy.

## Notes

No secrets are stored in the repository. Use `.env.example` as the local configuration template.
