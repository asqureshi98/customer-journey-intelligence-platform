-- One row per session, updated as new events arrive.
-- ReplacingMergeTree(updated_at) allows idempotent upserts: a later batch for
-- the same session_id wins because updated_at is newer.
CREATE TABLE IF NOT EXISTS customer_journey.session_metrics
(
    session_id          String,
    customer_id         Nullable(String),
    anonymous_id        Nullable(String),
    channel             LowCardinality(String),
    first_seen          DateTime64(3, 'UTC'),
    last_seen           DateTime64(3, 'UTC'),
    event_count         UInt32,
    max_journey_stage   LowCardinality(String),
    reached_checkout    UInt8,
    reached_payment     UInt8,
    converted           UInt8,
    funnel_collapse     UInt8,
    cart_value_at_abandon Nullable(Float64),
    updated_at          DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toDate(first_seen)
ORDER BY (session_id)
TTL toDate(first_seen) + INTERVAL 90 DAY;
