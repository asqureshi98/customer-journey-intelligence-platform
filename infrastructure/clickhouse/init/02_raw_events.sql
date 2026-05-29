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
