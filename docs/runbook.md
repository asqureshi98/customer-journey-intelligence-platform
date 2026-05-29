# Operational Runbook

This runbook covers the local Docker Compose stack for the Realtime Customer Journey Intelligence Platform. It is designed for a laptop or CI runner with Docker available; no paid cloud services or secrets are required.

## Prerequisites

- Python 3.11+
- Docker with the Compose plugin
- Project dependencies installed with `make setup`
- Optional local overrides copied from `.env.example` to `.env`

## Startup sequence

```bash
make docker-up
make wait-services
make create-topics
make generate-sample
```

`make docker-up` starts Redpanda, Redpanda Console, and ClickHouse. `make wait-services` polls local HTTP health endpoints until the stack is ready, then `make create-topics` creates `customer-events` and `customer-events-dlq` idempotently.

## Health checks

Docker Compose defines container healthchecks for:

- Redpanda: `rpk cluster health`
- Redpanda Console: HTTP probe on `http://localhost:8080/`
- ClickHouse: `clickhouse-client --user cji --password cji_local_password --query 'SELECT 1'`

Local readiness can also be checked without reading Docker metadata:

```bash
python scripts/wait_for_services.py --timeout 90
python scripts/wait_for_services.py --skip-console --timeout 30
```

The script probes:

- Redpanda admin readiness: `http://localhost:9644/v1/status/ready`
- Redpanda Console: `http://localhost:8080/`
- ClickHouse ping: `http://localhost:8123/ping`

## Common operations

```bash
# Run local quality gates
make check

# Run a no-Docker smoke path
make smoke-local

# Load generated sample data directly into ClickHouse
make load-clickhouse-sample

# Serve API endpoints on http://127.0.0.1:8000
make api-local

# Run the Spark -> ClickHouse raw sink, then publish sample events from another terminal
make stream-clickhouse
make publish-sample
```

Operational CLIs emit JSON structured logs with fields such as `event_count`, `topic`, `database`, `sink_mode`, and `checkpoint_path`. Set `CUSTOMER_JOURNEY_LOG_LEVEL` in `.env` to adjust verbosity.

## Troubleshooting

### `make wait-services` times out

1. Check container state: `docker compose ps`.
2. Inspect Redpanda logs: `docker compose logs redpanda`.
3. Inspect ClickHouse logs: `docker compose logs clickhouse`.
4. If only Console is slow or not needed, run `python scripts/wait_for_services.py --skip-console --timeout 30` to validate the broker and warehouse first.

### Redpanda topics are missing

Run `make create-topics` after `make wait-services`. The target is idempotent and safe to repeat.

### ClickHouse has stale local data

For a clean local warehouse, shut down with volume removal:

```bash
docker compose down -v
make docker-up
make wait-services
```

Use this only for local development because it deletes the Compose-managed ClickHouse volume.

### Spark streaming job cannot read Kafka

- Confirm `make wait-services` passes.
- Confirm `make create-topics` has run.
- Confirm `CUSTOMER_JOURNEY_KAFKA_BOOTSTRAP_SERVERS=localhost:19092` when running Spark on the host.
- Keep the checkpoint directory stable for repeatable ClickHouse writes, or delete `/tmp/cji-checkpoint` for a fresh local replay.

## Shutdown

```bash
make docker-down
```

Use `docker compose down -v` only when you intentionally want to remove the ClickHouse local data volume.

## CI expectations

The default GitHub Actions job runs the same local quality gate as developers: `make check`. The workflow also includes a Docker-dependent integration job that is disabled by default and documented as requiring Compose services; it is safe because it only runs when explicitly enabled by workflow dispatch.
