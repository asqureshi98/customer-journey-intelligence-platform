# Operational runbook

This runbook covers local operation of the customer journey intelligence platform. It assumes a laptop or CI runner with Python 3.11+ and Docker Compose. No paid cloud services are required.

## Prerequisites

- Python 3.11+
- Docker with the Compose plugin
- Project dependencies installed with `make setup`
- Optional dashboard dependencies installed with `make setup-dashboard`
- Optional local configuration copied from `.env.example` to `.env`

## Quality gates

```bash
make check
```

`make check` runs ruff format check, ruff lint, and the test suite. Use this before handing off changes.

## No-Docker smoke path

```bash
make smoke-local
```

This generates sample events and runs tests. It is the fastest way to verify contracts, generator behavior, aggregate helpers, and API/dashboard import paths without starting Redpanda or ClickHouse.

## Full local stack startup

```bash
make docker-up
make wait-services
make create-topics
make generate-sample
```

What starts:

- Redpanda broker on `localhost:19092`
- Redpanda Console on `http://localhost:8080`
- ClickHouse HTTP on `http://localhost:8123`
- ClickHouse native port on `localhost:9000`

`make wait-services` calls `scripts/wait_for_services.py`, which checks Redpanda admin readiness, Redpanda Console, and ClickHouse ping.

## Streaming demo paths

Console sink:

```bash
make stream-local
```

ClickHouse raw sink:

```bash
# Terminal 1
make stream-clickhouse

# Terminal 2
make publish-sample
```

The ClickHouse sink writes valid deduplicated events into `customer_journey.raw_events`. Invalid rows are visible in the Spark job output; live DLQ topic publishing is planned.

## API and dashboard

```bash
make load-clickhouse-sample
make api-local
```

Open `http://127.0.0.1:8000/docs` for the OpenAPI UI.

Optional dashboard:

```bash
make setup-dashboard
make dashboard-local
```

To use the local API for dashboard aggregate panels:

```bash
CJI_API_BASE_URL=http://127.0.0.1:8000 make dashboard-local
```

If the API is unavailable, the dashboard uses deterministic demo/fallback data and shows that state clearly.

## Health checks

```bash
python scripts/wait_for_services.py --timeout 90
python scripts/wait_for_services.py --skip-console --timeout 30
curl http://localhost:8123/ping
```

Docker Compose also defines healthchecks for Redpanda, Redpanda Console, and ClickHouse.

## Troubleshooting

### `make wait-services` times out

1. Run `docker compose ps`.
2. Inspect Redpanda logs with `docker compose logs redpanda`.
3. Inspect ClickHouse logs with `docker compose logs clickhouse`.
4. If Console is not needed, run `python scripts/wait_for_services.py --skip-console --timeout 30`.

### Topics are missing

Run `make create-topics`. It is idempotent and creates both `customer-events` and `customer-events-dlq`.

### Spark cannot read Kafka

- Confirm `make wait-services` passes.
- Confirm `make create-topics` has run.
- Confirm `CUSTOMER_JOURNEY_KAFKA_BOOTSTRAP_SERVERS=localhost:19092` for host-local Spark.
- Keep `/tmp/cji-checkpoint` stable for repeatable ClickHouse writes, or delete it for a fresh replay.

### ClickHouse has stale local data

For a clean local warehouse:

```bash
docker compose down -v
make docker-up
make wait-services
```

Only use volume removal for local development because it deletes the Compose-managed ClickHouse data.

## Shutdown

```bash
make docker-down
```

## Logging and configuration

Operational CLIs emit structured JSON logs with fields such as `event_count`, `topic`, `database`, `sink_mode`, and `checkpoint_path`. Set `CUSTOMER_JOURNEY_LOG_LEVEL` in `.env` to adjust verbosity.
