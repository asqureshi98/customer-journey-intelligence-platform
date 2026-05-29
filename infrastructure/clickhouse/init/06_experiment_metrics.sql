-- Per-window experiment attribution metrics.
-- ReplacingMergeTree(computed_at) allows a re-processed window to overwrite.
CREATE TABLE IF NOT EXISTS customer_journey.experiment_metrics
(
    window_start        DateTime64(3, 'UTC'),
    window_end          DateTime64(3, 'UTC'),
    experiment_id       LowCardinality(String),
    variant_id          LowCardinality(String),
    assigned_sessions   UInt64,
    exposed_sessions    UInt64,
    converted_sessions  UInt64,
    computed_at         DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(computed_at)
PARTITION BY toDate(window_start)
ORDER BY (window_start, experiment_id, variant_id)
TTL toDate(window_start) + INTERVAL 90 DAY;
