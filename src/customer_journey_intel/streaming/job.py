"""PySpark Structured Streaming pipeline entry point.

Sink modes
----------
console (default)
    Writes parsed events to stdout.  Useful for local debugging without Docker.
clickhouse
    Writes valid events to ClickHouse raw_events via foreachBatch.
    Requires ClickHouse to be running (``make docker-up``).
    Activate with ``--sink clickhouse``.

DLQ routing
-----------
Events where ``event.event_id IS NULL`` (JSON parse failure or missing field)
are isolated in ``invalid_df``.  The current implementation writes them to
the console for visibility.  To route them to the Redpanda DLQ topic, replace
the ``invalid_query`` sink with a ``foreachBatch`` that calls::

    from customer_journey_intel.streaming.dlq import (
        make_dlq_envelope, serialize_dlq_envelope, ErrorType,
    )
    producer.produce(topic="customer-events-dlq",
                     value=serialize_dlq_envelope(envelope))

Deduplication
-------------
Within each micro-batch, Spark's ``dropDuplicates(["event_id"])`` is applied
after a 10-minute watermark on ``occurred_at``.  This handles exact duplicate
deliveries from Redpanda.  ClickHouse aggregate tables additionally use
``ReplacingMergeTree`` for storage-level idempotency on re-processed windows.
"""

from __future__ import annotations

import argparse
import logging

from customer_journey_intel.common.logging import configure_logging
from customer_journey_intel.common.settings import Settings

logger = logging.getLogger(__name__)


def kafka_source_options(
    bootstrap_servers: str,
    topic: str,
    starting_offsets: str = "latest",
) -> dict[str, str]:
    """Return Spark Kafka source options for Redpanda-compatible brokers."""
    return {
        "kafka.bootstrap.servers": bootstrap_servers,
        "subscribe": topic,
        "startingOffsets": starting_offsets,
        "failOnDataLoss": "false",
    }


def build_event_projection_sql(source_view: str = "raw_events") -> str:
    """Projection used by the PySpark job after JSON parsing."""
    return f"""
    SELECT
      event.event_id AS event_id,
      event.event_name AS event_name,
      event.occurred_at AS occurred_at,
      event.received_at AS received_at,
      event.customer_id AS customer_id,
      event.anonymous_id AS anonymous_id,
      event.session_id AS session_id,
      event.journey_stage AS journey_stage,
      event.channel AS channel,
      event.properties AS properties,
      event.experiment_id AS experiment_id,
      event.variant_id AS variant_id
    FROM {source_view}
    WHERE event.event_id IS NOT NULL
    """


def checkpoint_location_options(path: str) -> dict[str, str]:
    """Return the Spark writeStream option enabling checkpointing at ``path``."""
    return {"checkpointLocation": path}


def run_stream(
    settings: Settings | None = None,
    sink_mode: str = "console",
    checkpoint_path: str = "/tmp/cji-checkpoint",
) -> None:
    """Run the PySpark Structured Streaming pipeline.

    Parameters
    ----------
    settings:
        Runtime configuration (Kafka/ClickHouse).  Defaults to env-loaded Settings.
    sink_mode:
        ``"console"`` (no external deps) or ``"clickhouse"`` (requires Docker).
    checkpoint_path:
        Filesystem path for Spark checkpoint metadata.  Used when ``sink_mode``
        is ``"clickhouse"`` to enable exactly-once delivery semantics.
    """
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col, from_json
    from pyspark.sql.types import MapType, StringType, StructField, StructType, TimestampType

    runtime_settings = settings or Settings()
    configure_logging(runtime_settings.log_level)
    logger.info(
        "starting structured streaming job",
        extra={
            "cji_sink_mode": sink_mode,
            "cji_topic": runtime_settings.kafka_topic,
            "cji_bootstrap_servers": runtime_settings.kafka_bootstrap_servers,
            "cji_checkpoint_path": checkpoint_path,
        },
    )

    spark = (
        SparkSession.builder.appName("customer-journey-intelligence")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )

    schema = StructType(
        [
            StructField("event_id", StringType(), nullable=False),
            StructField("event_name", StringType(), nullable=False),
            StructField("occurred_at", TimestampType(), nullable=False),
            StructField("received_at", TimestampType(), nullable=False),
            StructField("customer_id", StringType(), nullable=True),
            StructField("anonymous_id", StringType(), nullable=True),
            StructField("session_id", StringType(), nullable=False),
            StructField("journey_stage", StringType(), nullable=False),
            StructField("channel", StringType(), nullable=False),
            StructField("experiment_id", StringType(), nullable=True),
            StructField("variant_id", StringType(), nullable=True),
            StructField("properties", MapType(StringType(), StringType()), nullable=True),
        ]
    )

    raw = (
        spark.readStream.format("kafka")
        .options(
            **kafka_source_options(
                bootstrap_servers=runtime_settings.kafka_bootstrap_servers,
                topic=runtime_settings.kafka_topic,
            )
        )
        .load()
    )

    parsed = raw.select(
        col("value").cast("string").alias("raw_value"),
        from_json(col("value").cast("string"), schema).alias("event"),
    )
    parsed.createOrReplaceTempView("raw_events")

    valid_df = (
        spark.sql(build_event_projection_sql("raw_events"))
        .withWatermark("occurred_at", "10 minutes")
        .dropDuplicates(["event_id"])
    )

    # Invalid events: JSON parse failure yields a null struct; missing event_id
    # means the field was present but null.
    invalid_df = parsed.where("event IS NULL OR event.event_id IS NULL").select("raw_value")

    # --- Valid events sink ---
    if sink_mode == "clickhouse":
        logger.info(
            "configured clickhouse streaming sink",
            extra={"cji_database": runtime_settings.clickhouse_database},
        )
        from customer_journey_intel.storage.clickhouse import create_client
        from customer_journey_intel.streaming.sink import (
            checkpoint_location_options,
            make_foreachbatch_sink,
        )

        sink_fn = make_foreachbatch_sink(
            client_factory=lambda: create_client(runtime_settings),
            database=runtime_settings.clickhouse_database,
        )
        valid_query = (
            valid_df.writeStream.outputMode("append")
            .foreachBatch(sink_fn)
            .options(**checkpoint_location_options(checkpoint_path))
            .start()
        )
    else:
        valid_query = (
            valid_df.writeStream.outputMode("append")
            .format("console")
            .option("truncate", "false")
            .start()
        )

    # --- Invalid events: log to console; wire to DLQ Redpanda topic here ---
    invalid_query = (
        invalid_df.writeStream.outputMode("append")
        .format("console")
        .option("truncate", "false")
        .queryName("dlq-console")
        .start()
    )

    valid_query.awaitTermination()
    invalid_query.awaitTermination()


def main() -> None:
    parser = argparse.ArgumentParser(description="Customer Journey Intelligence streaming job.")
    parser.add_argument(
        "--sink",
        choices=["console", "clickhouse"],
        default="console",
        help="Output sink: 'console' (default, no Docker needed) or 'clickhouse'.",
    )
    parser.add_argument(
        "--checkpoint-dir",
        default="/tmp/cji-checkpoint",
        help="Checkpoint directory for Spark state (used with --sink clickhouse).",
    )
    args = parser.parse_args()
    run_stream(sink_mode=args.sink, checkpoint_path=args.checkpoint_dir)


if __name__ == "__main__":
    main()
