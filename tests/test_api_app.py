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
                "conversion_rate": 0.75,
            }
        ]

    def revenue_leakage(self):
        return [
            {
                "failure_reason": "issuer_declined",
                "failed_payments": 2,
                "at_risk_revenue": 178.0,
                "affected_sessions": 2,
            }
        ]

    def sessions(self):
        return [
            {
                "session_id": "sess_1",
                "event_count": 8,
                "max_stage": "retention",
                "converted": True,
                "funnel_collapse": False,
                "cart_value_at_abandon": None,
            }
        ]

    def experiments(self):
        return [
            {
                "experiment_id": "exp_checkout",
                "variant_id": "B",
                "assigned_sessions": 10,
                "exposed_sessions": 8,
                "converted_sessions": 3,
                "conversion_rate": 0.3,
            }
        ]


def test_api_exposes_customer_journey_analytics_endpoints():
    client = TestClient(create_app(repository=FakeAnalyticsRepository()))

    assert client.get("/health").json() == {"status": "ok", "service": "customer-journey-intel"}
    assert client.get("/funnel").json()[0]["journey_stage"] == "cart"
    assert client.get("/revenue-leakage").json()[0]["failed_payments"] == 2
    assert client.get("/sessions").json()[0]["max_stage"] == "retention"
    assert client.get("/experiments").json()[0]["variant_id"] == "B"
