PYTHON ?= python
PYTEST ?= $(PYTHON) -m pytest
RUFF ?= $(PYTHON) -m ruff
export PYTHONPATH := src

.PHONY: setup test lint format generate-sample docker-up docker-down

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

docker-up:
	docker compose up -d

docker-down:
	docker compose down
