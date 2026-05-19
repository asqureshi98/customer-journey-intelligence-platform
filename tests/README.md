# Tests

Unit tests for the Realtime Customer Journey Intelligence Platform.

## Important

All tests in this directory run without Docker or any external services.
No Redpanda broker, ClickHouse instance, or Spark cluster is required.

The PySpark streaming job tests validate helper functions (Kafka option builders,
SQL projection strings) directly in Python — no SparkSession is started during CI.

## Running the tests

```bash
# Install dependencies first (once)
make setup

# Run the full suite
make test

# Run with coverage report
make test-cov
```

## Structure

| File                       | What it covers                                              |
|----------------------------|-------------------------------------------------------------|
| `conftest.py`              | Shared fixtures: sample event dicts for all test modules    |
| `test_event_contracts.py`  | Pydantic `EcommerceEvent` validation — happy path and errors|
| `test_event_generator.py`  | `JourneySimulator` journey ordering and JSON serialization  |
| `test_streaming_job.py`    | Kafka source options and Spark SQL projection helpers       |

## Design principles

- Tests import only from `src/customer_journey_intel/` — no monkey-patching of external SDKs.
- Deterministic fixtures use fixed seeds and frozen datetimes so failures are reproducible.
- Integration tests (requiring Docker) will live under `tests/integration/` in a later sprint
  and are excluded from the default `make test` target.
