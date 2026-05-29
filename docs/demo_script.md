# Demo Script — Realtime Customer Journey Intelligence Platform

This walkthrough demonstrates the current local portfolio flow: generating synthetic journey data, creating Redpanda topics, running the PySpark Kafka reader or checkpointed Spark -> ClickHouse raw sink, loading raw JSONL events into ClickHouse for deterministic demos, querying the FastAPI analytics service, and optionally opening the Streamlit dashboard.

Estimated time: 15 minutes on a laptop with Docker installed.

## Prerequisites

- Docker Desktop or Docker Engine with Compose plugin
- Python 3.11+
- 4 GB free RAM (Redpanda 1 GB, ClickHouse 1.5 GB, Spark driver ~1 GB)

## Step 1 — Install the Python package

```bash
git clone https://github.com/your-org/customer-journey-intelligence-platform.git
cd customer-journey-intelligence-platform

make setup
# Installs pydantic, pyspark, confluent-kafka, clickhouse-connect, FastAPI, uvicorn, and dev tools
```

Verify:

```bash
python -c "import customer_journey_intel; print(customer_journey_intel.__version__)"
# 0.1.0
```

## Step 2 — Run the unit tests (no Docker needed)

```bash
make test
```

Expected output resembles:

```
collected <n> items
...
<n> passed in ...
```

The exact count changes as the portfolio adds coverage for streaming sinks, data quality, dashboard behavior, and operational hardening.

## Step 3 — Generate a sample dataset

```bash
make generate-sample
# Writes data/sample_events.jsonl with events from 5 customer journeys
```

Inspect the output:

```bash
head -3 data/sample_events.jsonl | python -m json.tool
```

You should see a `homepage_viewed` event followed by `search_performed` and
`product_viewed` events, all sharing the same `session_id`, with timestamps increasing
by a few seconds per event.

To generate a larger dataset (e.g. 50 journeys):

```bash
python -m customer_journey_intel.event_generator.cli \
    --journeys 50 \
    --output data/large_sample.jsonl \
    --seed 99
```

## Step 4 — Start the local infrastructure

```bash
make docker-up
```

This starts three services:
- **Redpanda** (Kafka broker) — `localhost:19092`
- **Redpanda Console** (web UI) — `http://localhost:8080`
- **ClickHouse** (analytics warehouse) — `http://localhost:8123`

Wait for all three services to become healthy (about 20–30 seconds):

```bash
docker compose ps
# All services should show "healthy" or "running"
```

Verify Redpanda:

```bash
docker compose exec redpanda rpk cluster health
# Healthy: true
```

Verify ClickHouse:

```bash
curl http://localhost:8123/ping
# Ok.
```

## Step 5 — Create Redpanda topics

```bash
make create-topics
```

Browse topics at http://localhost:8080 — you should see both topics listed.

## Step 6 — Produce sample events to Redpanda

Stream the generated JSONL file into the `customer-events` topic:

```bash
make publish-sample
```

Verify messages arrived:

```bash
docker compose exec redpanda rpk topic describe customer-events
```

Or browse to http://localhost:8080/topics/customer-events to see messages in the
Redpanda Console UI.

## Step 7 — Run the PySpark streaming job

In a new terminal:

```bash
make stream-local
```

The target sets `SPARK_SUBMIT_ARGS` for the Kafka connector and starts a local Spark session. The default console sink reads from the `customer-events` topic, parses JSON, separates invalid rows, applies a 10-minute watermark plus `event_id` dedupe, and prints projected valid fields in micro-batches:

```
-------------------------------------------
Batch: 0
-------------------------------------------
+--------------------------------------+-----------------+-------------------+
|event_id                              |event_name       |journey_stage      |
+--------------------------------------+-----------------+-------------------+
|018f4dd7-9a18-7c7a-b201-1f6d26cdd001 |homepage_viewed  |acquisition        |
|018f4dd7-9a18-7c7a-b201-1f6d26cdd002 |search_performed |discovery          |
|018f4dd7-9a18-7c7a-b201-1f6d26cdd003 |product_viewed   |consideration      |
...
```

To exercise the live ClickHouse raw sink instead, run this in a terminal after `make docker-up` and `make create-topics`:

```bash
make stream-clickhouse
```

Then run `make publish-sample` from another terminal. The ClickHouse sink uses Spark checkpointing at `/tmp/cji-checkpoint` and writes valid rows into `customer_journey.raw_events`. Invalid rows are printed for visibility; live publishing to `customer-events-dlq` is the remaining DLQ integration step.

To stop either streaming job: `Ctrl+C`

## Step 8 — Load sample data into ClickHouse and query analytics

The current scaffold includes a lightweight direct JSONL loader for local demos. It creates the
`raw_events` table and inserts the generated sample events:

```bash
make load-clickhouse-sample
```

Run a funnel query:

```sql
SELECT
    journey_stage,
    event_name,
    count() AS event_count,
    uniq(session_id) AS sessions
FROM raw_events
GROUP BY journey_stage, event_name
ORDER BY sessions DESC;
```

## Step 9 — Start the analytics API

```bash
make api-local
```

Open the generated OpenAPI docs at:

```text
http://127.0.0.1:8000/docs
```

Useful endpoints:

```text
GET /funnel
GET /sessions
GET /revenue-leakage
GET /experiments
```

## Step 10 — Stop services

```bash
make docker-down
```

## Troubleshooting

**Redpanda fails to start:** Increase Docker memory to at least 3 GB in Docker Desktop
preferences.

**PySpark fails with `java.lang.ClassNotFoundException: kafka`:** The Spark Kafka
connector is a runtime dependency. Run:

```bash
pip install pyspark[connect]
# or add the kafka connector JAR manually:
export SPARK_SUBMIT_ARGS="--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 pyspark-shell"
make stream-local
```

**ClickHouse `Connection refused`:** Wait an additional 10 seconds and retry. ClickHouse
takes longer to initialize on first boot (table directory creation).

**`make generate-sample` fails:** Ensure `data/` directory exists or let the command
create it automatically (it calls `mkdir -p data/` internally).
