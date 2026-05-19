# Project: Realtime Customer Journey Intelligence Platform

## Product concept
A production-inspired ecommerce data platform that turns synthetic customer behavior streams into real-time funnel analytics, revenue leakage alerts, experiment insights, and executive dashboards using PySpark Structured Streaming.

## Core differentiation
This is not a clone of a generic clickstream tutorial. It must use a custom customer journey simulator, richer event taxonomy, data contracts, late-arriving event handling, bad-event quarantine, funnel analytics, session metrics, and revenue leakage detection.

## MVP stack
- Python 3.11+
- PySpark Structured Streaming for streaming processing
- Redpanda as Kafka-compatible broker
- ClickHouse as real-time analytics warehouse
- Docker Compose for local services
- pytest, ruff, Pydantic for tests/contracts/linting
- Optional next milestones: MinIO + Parquet lake, dbt-clickhouse, Superset, Airflow, Great Expectations, Prometheus/Grafana

## Initial MVP requirements
1. Synthetic ecommerce event generator with realistic journeys.
2. Pydantic event contracts for event validation.
3. Redpanda topic publishing support via confluent-kafka.
4. PySpark Structured Streaming job that reads Kafka/Redpanda events, parses JSON, validates/normalizes schema, derives windows/funnel metrics, and writes a starter sink.
5. Local developer commands via Makefile.
6. Docker Compose skeleton for Redpanda and ClickHouse.
7. Tests that can run without requiring Docker services where possible.
8. Documentation with architecture, data model, and demo instructions.

## Event taxonomy
- homepage_viewed
- search_performed
- category_viewed
- product_viewed
- add_to_cart
- remove_from_cart
- checkout_started
- shipping_info_added
- payment_attempted
- payment_succeeded
- payment_failed
- order_completed
- experiment_assigned
- variant_exposed
- page_load_slow
- api_error_seen

## Engineering standards
- Keep Sprint 0 lightweight and runnable locally.
- Do not require paid cloud services.
- Never commit secrets or .env files.
- Include .env.example only.
- Prefer small, testable modules.
- Use clear README commands.
- Make CI pass with unit tests and static checks.

## Key commands to support
- make setup
- make test
- make lint
- make format
- make generate-sample
- make docker-up
- make docker-down

## Suggested package layout
- src/customer_journey_intel/event_generator/
- src/customer_journey_intel/contracts/
- src/customer_journey_intel/streaming/
- src/customer_journey_intel/common/
- tests/
- docs/
- infrastructure/
