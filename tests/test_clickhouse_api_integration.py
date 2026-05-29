import os

import pytest
from fastapi.testclient import TestClient

from customer_journey_intel.api.analytics import ClickHouseAnalyticsRepository
from customer_journey_intel.api.app import create_app

pytestmark = [pytest.mark.clickhouse, pytest.mark.api_integration]


def require_clickhouse():
    if os.getenv("CJI_RUN_CLICKHOUSE_TESTS") != "1":
        pytest.skip("set CJI_RUN_CLICKHOUSE_TESTS=1 with Docker Compose ClickHouse running")


def test_live_clickhouse_analytics_api_smoke():
    require_clickhouse()
    repository = ClickHouseAnalyticsRepository()
    client = TestClient(create_app(repository=repository))

    assert client.get("/health").status_code == 200
    for path in ("/funnel", "/revenue-leakage", "/sessions", "/experiments"):
        response = client.get(path)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
