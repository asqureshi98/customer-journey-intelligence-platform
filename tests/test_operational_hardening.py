from pathlib import Path

import pytest
from scripts.wait_for_services import ServiceCheck, check_service, wait_for_services


def test_env_example_covers_settings_prefixes():
    env_example = Path(".env.example").read_text(encoding="utf-8")

    assert "CUSTOMER_JOURNEY_KAFKA_BOOTSTRAP_SERVERS=" in env_example
    assert "CUSTOMER_JOURNEY_KAFKA_TOPIC=" in env_example
    assert "CUSTOMER_JOURNEY_CLICKHOUSE_HOST=" in env_example
    assert "CUSTOMER_JOURNEY_CLICKHOUSE_PORT=" in env_example
    assert "CUSTOMER_JOURNEY_CLICKHOUSE_DATABASE=" in env_example
    assert "CUSTOMER_JOURNEY_CLICKHOUSE_USER=" in env_example
    assert "CUSTOMER_JOURNEY_CLICKHOUSE_PASSWORD=" in env_example
    assert "CUSTOMER_JOURNEY_LOG_LEVEL=" in env_example


def test_compose_defines_service_healthchecks():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "redpanda:" in compose
    assert "redpanda-console:" in compose
    assert "clickhouse:" in compose
    assert compose.count("healthcheck:") >= 3
    assert "condition: service_healthy" in compose
    assert (
        "clickhouse-client --user cji --password cji_local_password --query 'SELECT 1'" in compose
    )


def test_wait_for_services_success(monkeypatch):
    calls = []

    def fake_check_service(check: ServiceCheck):
        calls.append(check.name)
        return True, "HTTP 200"

    monkeypatch.setattr("scripts.wait_for_services.check_service", fake_check_service)

    statuses = wait_for_services(
        [ServiceCheck("redpanda", "http://localhost:9644/v1/status/ready")],
        timeout_seconds=1,
        interval_seconds=0,
    )

    assert calls == ["redpanda"]
    assert statuses == {"redpanda": "HTTP 200"}


def test_wait_for_services_timeout(monkeypatch):
    monkeypatch.setattr(
        "scripts.wait_for_services.check_service",
        lambda check: (False, "connection refused"),
    )

    with pytest.raises(TimeoutError, match="redpanda"):
        wait_for_services(
            [ServiceCheck("redpanda", "http://localhost:9644/v1/status/ready")],
            timeout_seconds=0,
            interval_seconds=0,
        )


def test_check_service_requires_expected_text(monkeypatch):
    monkeypatch.setattr(
        "scripts.wait_for_services._http_get", lambda url, timeout: (200, "Not ready")
    )

    ready, detail = check_service(ServiceCheck("clickhouse", "http://localhost:8123/ping", "Ok"))

    assert ready is False
    assert "missing 'Ok'" in detail
