from pathlib import Path

from customer_journey_intel.dashboard.data import (
    demo_dashboard_data,
    executive_summary,
    load_dashboard_data,
    read_raw_events,
)


def test_dashboard_demo_payload_contains_required_sections():
    payload = demo_dashboard_data()

    assert {
        "funnel",
        "revenue_leakage",
        "experiments",
        "sessions",
        "raw_events",
        "metadata",
    }.issubset(payload)
    assert payload["metadata"]["source"] == "demo"
    assert executive_summary(payload)["at_risk_revenue"] > 0


def test_dashboard_import_does_not_require_streamlit():
    import customer_journey_intel.dashboard.app as dashboard_app

    assert callable(dashboard_app.main)


def test_read_raw_events_flattens_sample_jsonl(tmp_path: Path):
    sample_path = tmp_path / "events.jsonl"
    sample_path.write_text(
        '{"event_id":"evt_1","event_name":"payment_failed","journey_stage":"checkout",'
        '"session_id":"sess_1","customer_id":"cust_1","anonymous_id":null,'
        '"channel":"paid_search","occurred_at":"2026-05-28T12:00:00Z",'
        '"properties":{"failure_reason":"issuer_declined","cart_value":42.5}}\n',
        encoding="utf-8",
    )

    rows = read_raw_events(sample_path)

    assert rows == [
        {
            "event_id": "evt_1",
            "event_name": "payment_failed",
            "journey_stage": "checkout",
            "session_id": "sess_1",
            "customer_id": "cust_1",
            "anonymous_id": None,
            "channel": "paid_search",
            "occurred_at": "2026-05-28T12:00:00Z",
            "cart_value": 42.5,
            "failure_reason": "issuer_declined",
        }
    ]


def test_load_dashboard_data_uses_sample_events_without_api(tmp_path: Path):
    sample_path = tmp_path / "events.jsonl"
    sample_path.write_text(
        '{"event_id":"evt_2","event_name":"order_completed","journey_stage":"retention",'
        '"session_id":"sess_2","channel":"organic","occurred_at":"2026-05-28T12:05:00Z",'
        '"properties":{"order_total":99.0}}\n',
        encoding="utf-8",
    )

    payload = load_dashboard_data(sample_events_path=sample_path)

    assert payload["metadata"]["source"] == "demo"
    assert payload["raw_events"][0]["order_total"] == 99.0
