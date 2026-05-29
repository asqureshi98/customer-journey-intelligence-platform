# ClickHouse — Local Setup Notes

ClickHouse is the local analytics warehouse. Docker init SQL creates the `customer_journey` database plus `raw_events`, `funnel_metrics`, `session_metrics`, `revenue_events`, and `experiment_metrics`. Sprint 2 writes valid raw events through the Spark `foreachBatch` sink or the direct JSONL loader; aggregate metric writers are still planned.

## Starting ClickHouse

```bash
# From the project root
make docker-up

# Or directly
docker compose up -d clickhouse
```

## Connection details

| Parameter | Value                         |
|-----------|-------------------------------|
| HTTP API  | http://localhost:8123         |
| Native TCP| localhost:9000                |
| Database  | `customer_journey`            |
| User      | `cji`                         |
| Password  | `cji_local_password`          |

## Verifying the server is up

```bash
curl http://localhost:8123/ping
# Expected response: Ok.
```

## Connecting with the ClickHouse client

```bash
docker compose exec clickhouse clickhouse-client \
  --user cji \
  --password cji_local_password \
  --database customer_journey
```

## DDL

Authoritative schema files live in `infrastructure/clickhouse/init/` and are mounted into `/docker-entrypoint-initdb.d` by Docker Compose:

- `01_database.sql` — creates `customer_journey`
- `02_raw_events.sql` — raw event table using `ReplacingMergeTree(ingested_at)` ordered by `event_id` for idempotent replays
- `03_funnel_metrics.sql` — windowed funnel metric target schema
- `04_session_metrics.sql` — per-session metric target schema
- `05_revenue_events.sql` — payment/revenue event target schema
- `06_experiment_metrics.sql` — experiment metric target schema

The Python helpers in `customer_journey_intel.storage.clickhouse` generate matching DDL for tests and local loader setup.

### raw_events

```sql
CREATE TABLE IF NOT EXISTS customer_journey.raw_events
(
    event_id        String,
    event_name      LowCardinality(String),
    occurred_at     DateTime64(3, 'UTC'),
    received_at     DateTime64(3, 'UTC'),
    customer_id     Nullable(String),
    anonymous_id    Nullable(String),
    session_id      String,
    journey_stage   LowCardinality(String),
    channel         LowCardinality(String),
    experiment_id   Nullable(String),
    variant_id      Nullable(String),
    properties      String,
    ingested_at     DateTime64(3, 'UTC') DEFAULT now64(3),
    ingest_date     Date DEFAULT toDate(occurred_at)
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY ingest_date
ORDER BY (event_id)
TTL ingest_date + INTERVAL 90 DAY;
```

The metric schemas are intentionally created now but not populated by the Sprint 2 Spark job yet. Populate them in a future streaming branch after the raw path is stable.

## Data retention

The `raw_events` table uses a 90-day TTL. Metric tables also use 90-day TTLs in the init SQL so local development volumes stay bounded.

## Useful queries

### Planned funnel conversion by stage (last 60 minutes)

```sql
SELECT
    journey_stage,
    sum(event_count) AS events,
    sum(session_count) AS sessions
FROM customer_journey.funnel_metrics
WHERE window_start >= now() - INTERVAL 60 MINUTE
GROUP BY journey_stage
ORDER BY sessions DESC;
```

### Planned revenue leakage in the last hour

```sql
SELECT
    payment_method,
    count() AS failed_payments,
    sum(cart_value) AS at_risk_revenue
FROM customer_journey.revenue_events
WHERE leakage = 1
  AND occurred_at >= now() - INTERVAL 60 MINUTE
GROUP BY payment_method
ORDER BY at_risk_revenue DESC;
```
