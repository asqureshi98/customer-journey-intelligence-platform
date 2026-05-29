# Redpanda — Local Setup Notes

Redpanda is a Kafka-compatible streaming platform that runs as a single binary with no
ZooKeeper dependency. The platform uses it as the local message broker for customer
journey events.

## Topics

| Topic name              | Partition key | Purpose                                      |
|-------------------------|---------------|----------------------------------------------|
| `customer-events`       | `session_id`  | Primary validated event stream               |
| `customer-events-dlq`   | none          | Dead-letter queue for schema-invalid events  |

Partitioning by `session_id` ensures all events from a single customer session land on
the same partition. This lets the PySpark streaming job perform session-scoped stateful
aggregations without shuffle overhead.

## Starting Redpanda

```bash
# From the project root
make docker-up

# Or directly
docker compose up -d redpanda redpanda-console
```

## Checking broker health

```bash
docker compose exec redpanda rpk cluster health
```

## Creating topics manually

Create topics before publishing or running the streaming job:

```bash
docker compose exec redpanda rpk topic create customer-events \
  --partitions 4 \
  --replicas 1

docker compose exec redpanda rpk topic create customer-events-dlq \
  --partitions 1 \
  --replicas 1
```

## Producing sample events

After running `make generate-sample`, seed Redpanda with the generated events:

```bash
docker compose exec -T redpanda rpk topic produce customer-events \
  < data/sample_events.jsonl
```

## Redpanda Console

Browse topics, messages, and consumer groups at http://localhost:8080 once `make docker-up`
has completed.

## Configuration notes

The broker listens on two advertised addresses:
- `PLAINTEXT://redpanda:9092` — internal Docker network address used by Spark and Console
- `OUTSIDE://localhost:19092` — external address for the host machine CLI tools

The `.env.example` uses `localhost:19092` as `CUSTOMER_JOURNEY_KAFKA_BOOTSTRAP_SERVERS`
so local Python scripts connect via the external listener.
