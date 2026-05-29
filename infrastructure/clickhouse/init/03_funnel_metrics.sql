-- Tumbling-window funnel aggregates written by the Spark foreachBatch sink.
-- ReplacingMergeTree deduplicates on (window_start, journey_stage, event_name,
-- experiment_id, variant_id) using computed_at as the version column so a
-- re-processed window overwrites the previous aggregate.
CREATE TABLE IF NOT EXISTS customer_journey.funnel_metrics
(
    window_start    DateTime64(3, 'UTC'),
    window_end      DateTime64(3, 'UTC'),
    journey_stage   LowCardinality(String),
    event_name      LowCardinality(String),
    session_count   UInt64,
    event_count     UInt64,
    experiment_id   LowCardinality(String),
    variant_id      LowCardinality(String),
    computed_at     DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(computed_at)
PARTITION BY toDate(window_start)
ORDER BY (window_start, journey_stage, event_name, experiment_id, variant_id)
TTL toDate(window_start) + INTERVAL 90 DAY;
