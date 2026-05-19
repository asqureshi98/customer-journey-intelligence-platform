from customer_journey_intel.streaming.job import build_event_projection_sql, kafka_source_options


def test_kafka_source_options_target_redpanda_topic():
    options = kafka_source_options(
        bootstrap_servers="redpanda:9092",
        topic="customer-events",
        starting_offsets="earliest",
    )

    assert options == {
        "kafka.bootstrap.servers": "redpanda:9092",
        "subscribe": "customer-events",
        "startingOffsets": "earliest",
        "failOnDataLoss": "false",
    }


def test_streaming_projection_contains_customer_journey_fields():
    sql = build_event_projection_sql(source_view="raw_events")

    assert "event_name" in sql
    assert "journey_stage" in sql
    assert "customer_id" in sql
    assert "properties" in sql
