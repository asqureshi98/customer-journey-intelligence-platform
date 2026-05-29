-- Revenue-relevant events extracted from raw_events for leakage analysis.
-- Covers: payment_attempted, payment_succeeded, payment_failed, order_completed.
CREATE TABLE IF NOT EXISTS customer_journey.revenue_events
(
    event_id        String,
    session_id      String,
    customer_id     Nullable(String),
    event_name      LowCardinality(String),
    occurred_at     DateTime64(3, 'UTC'),
    cart_value      Nullable(Float64),
    product_id      Nullable(String),
    order_id        Nullable(String),
    payment_method  Nullable(String),
    failure_reason  Nullable(String),
    leakage         UInt8,
    resolution      LowCardinality(String),
    experiment_id   LowCardinality(String),
    variant_id      LowCardinality(String),
    ingest_date     Date DEFAULT toDate(occurred_at)
)
ENGINE = ReplacingMergeTree()
PARTITION BY ingest_date
ORDER BY (occurred_at, session_id, event_id)
TTL ingest_date + INTERVAL 90 DAY;
