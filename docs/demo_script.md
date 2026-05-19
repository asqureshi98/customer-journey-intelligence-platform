# Demo Script — Realtime Customer Journey Intelligence Platform

This walkthrough demonstrates Sprint 0 end-to-end: generating synthetic journey data,
publishing it to Redpanda, running the PySpark streaming job, and querying ClickHouse.

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
# Installs pydantic, pyspark, confluent-kafka, faker, structlog, and dev tools
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

Expected output:

```
collected 7 items
tests/test_event_contracts.py ...
tests/test_event_generator.py ..
tests/test_streaming_job.py ..
7 passed in 0.11s
```

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
docker compose -f infrastructure/docker-compose.yml ps
# All services should show "healthy" or "running"
```

Verify Redpanda:

```bash
docker exec journey_redpanda rpk cluster health
# Healthy: true
```

Verify ClickHouse:

```bash
curl http://localhost:8123/ping
# Ok.
```

## Step 5 — Create Redpanda topics

```bash
docker exec journey_redpanda rpk topic create customer-events \
    --partitions 4 \
    --replicas 1

docker exec journey_redpanda rpk topic create customer-events-dlq \
    --partitions 1 \
    --replicas 1
```

Browse topics at http://localhost:8080 — you should see both topics listed.

## Step 6 — Produce sample events to Redpanda

Stream the generated JSONL file into the `customer-events` topic:

```bash
docker exec -i journey_redpanda rpk topic produce customer-events \
    < data/sample_events.jsonl
```

Verify messages arrived:

```bash
docker exec journey_redpanda rpk topic describe customer-events
```

Or browse to http://localhost:8080/topics/customer-events to see messages in the
Redpanda Console UI.

## Step 7 — Run the PySpark streaming job

In a new terminal:

```bash
make stream-local
```

The job starts a local Spark session, reads from the `customer-events` topic, parses
JSON, and prints the projected event fields to the console in micro-batch format:

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

To stop the job: `Ctrl+C`

## Step 8 — Query ClickHouse (Sprint 1 target)

The Sprint 0 streaming sink writes to console. In Sprint 1, the sink writes to
ClickHouse. For now, you can manually insert the sample events and run analytic queries
to validate the schema.

Connect to ClickHouse:

```bash
docker exec -it journey_clickhouse clickhouse-client \
    --user default \
    --database customer_journey
```

Create the `raw_events` table (paste the DDL from `infrastructure/clickhouse/README.md`),
then insert from a file:

```sql
-- In the ClickHouse CLI after table creation:
INSERT INTO raw_events
    SELECT
        event_id, event_name, occurred_at, received_at,
        customer_id, anonymous_id, session_id,
        journey_stage, channel, experiment_id, variant_id,
        toString(properties) AS properties,
        toDate(occurred_at) AS ingest_date
    FROM file('/tmp/sample_events.jsonl', 'JSONEachRow');
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

## Step 9 — Stop services

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
