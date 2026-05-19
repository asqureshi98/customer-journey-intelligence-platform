from fastapi.testclient import TestClient

from customer_journey_intel.api.app import create_app


class FakeAnalyticsRepository:
    def funnel(self):
        return [
            {
                "journey_stage": "cart",
                "event_name": "add_to_cart",
                "event_count": 4,
                "sessions": 3,
            }
        ]

    def revenue_leakage(self):
        return [
            {
                "failure_reason": "issuer_declined",
                "failed_payments": 2,
                "at_risk_revenue": 178.0,
            }
        ]

    def sessions(self):
        return [{"session_id": "sess_1", "event_count": 8, "max_stage": "retention"}]

    def experiments(self):
        return [{"experiment_id": "exp_checkout", "variant_id": "B", "events": 10}]


def test_api_exposes_customer_journey_analytics_endpoints():
    client = TestClient(create_app(repository=FakeAnalyticsRepository()))

    assert client.get("/health").json() == {"status": "ok", "service": "customer-journey-intel"}
    assert client.get("/funnel").json()[0]["journey_stage"] == "cart"
    assert client.get("/revenue-leakage").json()[0]["failed_payments"] == 2
    assert client.get("/sessions").json()[0]["max_stage"] == "retention"
    assert client.get("/experiments").json()[0]["variant_id"] == "B"
