from __future__ import annotations

from customer_journey_intel.common.settings import Settings


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
    """Projection used by the starter PySpark job after JSON parsing."""

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


def run_stream(settings: Settings | None = None) -> None:
    """Run a lightweight PySpark Structured Streaming pipeline.

    Sprint 0 keeps the sink as console output so the job can be exercised before
    ClickHouse tables are finalized. The local Docker stack already includes
    ClickHouse for the next integration milestone.
    """

    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col, from_json
    from pyspark.sql.types import MapType, StringType, StructField, StructType, TimestampType

    runtime_settings = settings or Settings()
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

    parsed = raw.select(from_json(col("value").cast("string"), schema).alias("event"))
    parsed.createOrReplaceTempView("raw_events")
    projected = spark.sql(build_event_projection_sql("raw_events"))

    query = (
        projected.writeStream.outputMode("append")
        .format("console")
        .option("truncate", "false")
        .start()
    )
    query.awaitTermination()


def main() -> None:
    run_stream()


if __name__ == "__main__":
    main()
