# ClickHouse — Local Setup Notes

ClickHouse is the real-time analytics warehouse that stores enriched journey events,
funnel metrics, session KPIs, and revenue leakage records produced by the PySpark
streaming job.

## Starting ClickHouse

```bash
# From the project root
make docker-up

# Or directly
docker compose -f infrastructure/docker-compose.yml up -d clickhouse
```

## Connection details

| Parameter | Value                         |
|-----------|-------------------------------|
| HTTP API  | http://localhost:8123         |
| Native TCP| localhost:9000                |
| Database  | `customer_journey`            |
| User      | `default`                     |
| Password  | (empty in dev; see .env)      |

## Verifying the server is up

```bash
curl http://localhost:8123/ping
# Expected response: Ok.
```

## Connecting with the ClickHouse client

```bash
docker exec -it journey_clickhouse clickhouse-client \
  --user default \
  --database customer_journey
```

## Sprint 0 DDL

The tables below are the target schema for Sprint 1 integration. They can be created
manually via the ClickHouse client or automated with a migration script in a later sprint.

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
    properties      String,    -- JSON blob
    ingest_date     Date DEFAULT toDate(occurred_at)
)
ENGINE = MergeTree()
PARTITION BY ingest_date
ORDER BY (occurred_at, session_id, event_id)
TTL ingest_date + INTERVAL 90 DAY;
```

### funnel_metrics

```sql
CREATE TABLE IF NOT EXISTS customer_journey.funnel_metrics
(
    window_start        DateTime64(3, 'UTC'),
    window_end          DateTime64(3, 'UTC'),
    journey_stage       LowCardinality(String),
    event_name          LowCardinality(String),
    channel             LowCardinality(String),
    experiment_id       Nullable(String),
    variant_id          Nullable(String),
    event_count         UInt64,
    unique_sessions     UInt64,
    unique_customers    UInt64
)
ENGINE = AggregatingMergeTree()
ORDER BY (window_start, journey_stage, event_name, channel)
PARTITION BY toDate(window_start);
```

### session_metrics

```sql
CREATE TABLE IF NOT EXISTS customer_journey.session_metrics
(
    session_id              String,
    customer_id             Nullable(String),
    anonymous_id            Nullable(String),
    channel                 LowCardinality(String),
    session_start           DateTime64(3, 'UTC'),
    session_end             DateTime64(3, 'UTC'),
    session_duration_sec    UInt32,
    event_count             UInt16,
    max_funnel_stage        LowCardinality(String),
    funnel_collapse         UInt8,
    cart_value_at_abandon   Nullable(Float64),
    experiment_id           Nullable(String),
    variant_id              Nullable(String),
    updated_at              DateTime64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY session_id
PARTITION BY toDate(session_start);
```

### revenue_events

```sql
CREATE TABLE IF NOT EXISTS customer_journey.revenue_events
(
    event_id            String,
    session_id          String,
    customer_id         Nullable(String),
    occurred_at         DateTime64(3, 'UTC'),
    event_name          LowCardinality(String),
    payment_method      Nullable(LowCardinality(String)),
    cart_value          Nullable(Float64),
    currency            LowCardinality(String) DEFAULT 'USD',
    leakage             UInt8 DEFAULT 0,
    resolution          LowCardinality(String) DEFAULT 'resolved',
    failure_reason      Nullable(String),
    experiment_id       Nullable(String),
    variant_id          Nullable(String)
)
ENGINE = MergeTree()
ORDER BY (occurred_at, session_id, event_id)
PARTITION BY toDate(occurred_at);
```

## Data retention

The `raw_events` table uses a 90-day TTL. Aggregated tables (`funnel_metrics`,
`session_metrics`, `revenue_events`) do not have a TTL set by default and are expected
to grow slowly enough to be managed manually in a local dev environment.

## Useful queries

### Funnel conversion by stage (last 60 minutes)

```sql
SELECT
    journey_stage,
    sumMerge(event_count) AS events,
    uniqMerge(unique_sessions) AS sessions
FROM customer_journey.funnel_metrics
WHERE window_start >= now() - INTERVAL 60 MINUTE
GROUP BY journey_stage
ORDER BY sessions DESC;
```

### Revenue leakage in the last hour

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
