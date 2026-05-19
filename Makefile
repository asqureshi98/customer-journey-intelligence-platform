PYTHON ?= python
PYTEST ?= $(PYTHON) -m pytest
RUFF ?= $(PYTHON) -m ruff
export PYTHONPATH := src

.PHONY: setup test lint format generate-sample publish-sample stream-local load-clickhouse-sample api-local docker-up docker-down

setup:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTEST) tests

lint:
	$(RUFF) check .

format:
	$(RUFF) format .
	$(RUFF) check --fix .

generate-sample:
	$(PYTHON) -m customer_journey_intel.event_generator.cli --journeys 5 --output data/sample_events.jsonl

publish-sample:
	$(PYTHON) -m customer_journey_intel.event_generator.producer --input data/sample_events.jsonl

stream-local:
	SPARK_SUBMIT_ARGS="--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 pyspark-shell" $(PYTHON) -m customer_journey_intel.streaming.job

load-clickhouse-sample:
	$(PYTHON) -m customer_journey_intel.storage.clickhouse --input data/sample_events.jsonl

api-local:
	$(PYTHON) -m uvicorn customer_journey_intel.api.app:app --host 127.0.0.1 --port 8000 --reload

docker-up:
	docker compose up -d

docker-down:
	docker compose down
