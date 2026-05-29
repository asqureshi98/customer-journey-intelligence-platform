PYTHON ?= python
PYTEST ?= $(PYTHON) -m pytest
RUFF ?= $(PYTHON) -m ruff
export PYTHONPATH := src

.PHONY: setup test lint format check \
        generate-sample publish-sample \
        stream-local stream-clickhouse \
        load-clickhouse-sample \
        create-topics wait-services \
        smoke-local e2e-local \
        api-local dashboard-local setup-dashboard \
        docker-up docker-down

setup:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTEST) tests

lint:
	$(RUFF) check .

format:
	$(RUFF) format .
	$(RUFF) check --fix .

check:
	$(RUFF) format --check src tests scripts
	$(RUFF) check src tests scripts
	$(PYTEST) tests -q

# ── Event generation ──────────────────────────────────────────────────────────

generate-sample:
	$(PYTHON) -m customer_journey_intel.event_generator.cli --journeys 5 --output data/sample_events.jsonl

publish-sample:
	$(PYTHON) -m customer_journey_intel.event_generator.producer --input data/sample_events.jsonl

# ── Streaming ─────────────────────────────────────────────────────────────────

# Console sink — no Docker needed, useful for schema/parse debugging.
stream-local:
	SPARK_SUBMIT_ARGS="--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 pyspark-shell" \
	$(PYTHON) -m customer_journey_intel.streaming.job --sink console

# ClickHouse sink — requires: make docker-up && make create-topics
stream-clickhouse:
	SPARK_SUBMIT_ARGS="--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 pyspark-shell" \
	$(PYTHON) -m customer_journey_intel.streaming.job --sink clickhouse --checkpoint-dir /tmp/cji-checkpoint

# ── ClickHouse ────────────────────────────────────────────────────────────────

load-clickhouse-sample:
	$(PYTHON) -m customer_journey_intel.storage.clickhouse --input data/sample_events.jsonl --replace-existing

# ── Redpanda topics ───────────────────────────────────────────────────────────

# Creates customer-events (3 partitions) and customer-events-dlq (1 partition).
# Requires: make docker-up first.
create-topics:
	docker compose exec redpanda rpk topic create customer-events --partitions 3 --replicas 1 2>/dev/null || true
	docker compose exec redpanda rpk topic create customer-events-dlq --partitions 1 --replicas 1 2>/dev/null || true
	@echo "Topics ready: customer-events, customer-events-dlq"

wait-services:
	$(PYTHON) scripts/wait_for_services.py --timeout 90

# ── Smoke & end-to-end ────────────────────────────────────────────────────────

# smoke-local: runs entirely without Docker (generate events + all unit tests).
smoke-local: generate-sample
	$(PYTEST) tests -q
	@echo "Smoke passed: sample events generated and all unit tests pass"

# e2e-local: starts the full Docker stack and loads sample data into ClickHouse.
# After this completes, run 'make stream-clickhouse' in a separate terminal,
# then 'make publish-sample' to push events through the live pipeline.
e2e-local: docker-up
	$(MAKE) wait-services
	$(MAKE) create-topics
	$(MAKE) generate-sample
	$(MAKE) load-clickhouse-sample
	@echo "e2e stack ready."
	@echo "  Next: open two terminals and run:"
	@echo "    Terminal 1: make stream-clickhouse"
	@echo "    Terminal 2: make publish-sample"

# ── API and dashboard ─────────────────────────────────────────────────────────

api-local:
	$(PYTHON) -m uvicorn customer_journey_intel.api.app:app --host 127.0.0.1 --port 8000 --reload

setup-dashboard:
	$(PYTHON) -m pip install -e ".[dashboard]"

dashboard-local:
	$(PYTHON) -m streamlit run src/customer_journey_intel/dashboard/app.py

# ── Docker ────────────────────────────────────────────────────────────────────

docker-up:
	docker compose up -d

docker-down:
	docker compose down
