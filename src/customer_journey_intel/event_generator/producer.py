from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from customer_journey_intel.common.settings import Settings

ProducerFactory = Callable[[dict[str, str]], Any]


def _default_producer_factory(config: dict[str, str]) -> Any:
    from confluent_kafka import Producer

    return Producer(config)


def _message_key(line: str) -> str | None:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    return payload.get("session_id") or payload.get("customer_id") or payload.get("event_id")


def publish_json_lines(
    lines: Iterable[str],
    topic: str,
    bootstrap_servers: str,
    producer_factory: ProducerFactory = _default_producer_factory,
) -> int:
    """Publish JSON Lines events to a Kafka/Redpanda topic.

    The function accepts an injectable producer factory so tests can verify the
    publishing contract without requiring Docker or a live broker.
    """

    producer = producer_factory({"bootstrap.servers": bootstrap_servers})
    count = 0
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        producer.produce(topic=topic, key=_message_key(line), value=line, callback=None)
        producer.poll(0)
        count += 1
    producer.flush()
    return count


def publish_file(
    path: Path,
    topic: str | None = None,
    bootstrap_servers: str | None = None,
) -> int:
    settings = Settings()
    resolved_topic = topic or settings.kafka_topic
    resolved_bootstrap = bootstrap_servers or settings.kafka_bootstrap_servers
    with path.open(encoding="utf-8") as handle:
        return publish_json_lines(
            lines=handle,
            topic=resolved_topic,
            bootstrap_servers=resolved_bootstrap,
        )


def main() -> None:
    settings = Settings()
    parser = argparse.ArgumentParser(description="Publish generated journey JSONL to Redpanda.")
    parser.add_argument("--input", type=Path, default=Path("data/sample_events.jsonl"))
    parser.add_argument("--topic", default=settings.kafka_topic)
    parser.add_argument("--bootstrap-servers", default=settings.kafka_bootstrap_servers)
    args = parser.parse_args()

    count = publish_file(
        path=args.input,
        topic=args.topic,
        bootstrap_servers=args.bootstrap_servers,
    )
    print(f"published {count} events to {args.topic} via {args.bootstrap_servers}")


if __name__ == "__main__":
    main()
