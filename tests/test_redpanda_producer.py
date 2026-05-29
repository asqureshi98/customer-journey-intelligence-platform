from customer_journey_intel.event_generator.producer import publish_json_lines


class FakeProducer:
    def __init__(self, config):
        self.config = config
        self.messages = []
        self.flushed = False

    def produce(self, topic, key, value, callback=None):
        self.messages.append({"topic": topic, "key": key, "value": value, "callback": callback})

    def poll(self, timeout):
        self.poll_timeout = timeout

    def flush(self):
        self.flushed = True


def test_publish_json_lines_sends_events_to_configured_redpanda_topic():
    created_producers = []
    lines = [
        '{"event_id":"e1","session_id":"sess_1","event_name":"homepage_viewed"}',
        '{"event_id":"e2","session_id":"sess_1","event_name":"product_viewed"}',
    ]

    count = publish_json_lines(
        lines=lines,
        topic="customer-events",
        bootstrap_servers="localhost:19092",
        producer_factory=lambda config: (
            created_producers.append(FakeProducer(config)) or created_producers[-1]
        ),
    )

    producer = created_producers[0]
    assert count == 2
    assert producer.config == {"bootstrap.servers": "localhost:19092"}
    assert [message["topic"] for message in producer.messages] == [
        "customer-events",
        "customer-events",
    ]
    assert [message["key"] for message in producer.messages] == ["sess_1", "sess_1"]
    assert producer.messages[0]["value"] == lines[0]
    assert producer.flushed is True
