from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

DashboardPayload = dict[str, list[dict[str, Any]] | dict[str, Any]]

DEMO_FUNNEL: list[dict[str, Any]] = [
    {
        "journey_stage": "acquisition",
        "event_name": "homepage_viewed",
        "event_count": 1280,
        "sessions": 1000,
        "conversion_rate": 1.0,
    },
    {
        "journey_stage": "discovery",
        "event_name": "product_viewed",
        "event_count": 1840,
        "sessions": 742,
        "conversion_rate": 0.742,
    },
    {
        "journey_stage": "cart",
        "event_name": "add_to_cart",
        "event_count": 612,
        "sessions": 318,
        "conversion_rate": 0.318,
    },
    {
        "journey_stage": "checkout",
        "event_name": "checkout_started",
        "event_count": 286,
        "sessions": 221,
        "conversion_rate": 0.221,
    },
    {
        "journey_stage": "retention",
        "event_name": "order_completed",
        "event_count": 147,
        "sessions": 139,
        "conversion_rate": 0.139,
    },
]

DEMO_REVENUE_LEAKAGE: list[dict[str, Any]] = [
    {
        "failure_reason": "issuer_declined",
        "failed_payments": 34,
        "at_risk_revenue": 8420.75,
        "affected_sessions": 31,
    },
    {
        "failure_reason": "gateway_timeout",
        "failed_payments": 18,
        "at_risk_revenue": 4631.20,
        "affected_sessions": 17,
    },
    {
        "failure_reason": "cart_abandoned_after_slow_page",
        "failed_payments": 12,
        "at_risk_revenue": 2984.00,
        "affected_sessions": 12,
    },
]

DEMO_EXPERIMENTS: list[dict[str, Any]] = [
    {
        "experiment_id": "checkout_copy",
        "variant_id": "A",
        "assigned_sessions": 420,
        "exposed_sessions": 386,
        "converted_sessions": 52,
        "conversion_rate": 0.124,
    },
    {
        "experiment_id": "checkout_copy",
        "variant_id": "B",
        "assigned_sessions": 436,
        "exposed_sessions": 401,
        "converted_sessions": 67,
        "conversion_rate": 0.154,
    },
    {
        "experiment_id": "free_shipping_banner",
        "variant_id": "holdout",
        "assigned_sessions": 390,
        "exposed_sessions": 355,
        "converted_sessions": 43,
        "conversion_rate": 0.110,
    },
    {
        "experiment_id": "free_shipping_banner",
        "variant_id": "treatment",
        "assigned_sessions": 402,
        "exposed_sessions": 372,
        "converted_sessions": 59,
        "conversion_rate": 0.147,
    },
]

DEMO_SESSIONS: list[dict[str, Any]] = [
    {
        "session_id": "sess_demo_001",
        "event_count": 11,
        "max_stage": "retention",
        "first_seen": "2026-05-28T09:10:00Z",
        "last_seen": "2026-05-28T09:24:33Z",
        "converted": True,
        "funnel_collapse": False,
        "cart_value_at_abandon": None,
    },
    {
        "session_id": "sess_demo_002",
        "event_count": 8,
        "max_stage": "checkout",
        "first_seen": "2026-05-28T10:02:18Z",
        "last_seen": "2026-05-28T10:17:41Z",
        "converted": False,
        "funnel_collapse": True,
        "cart_value_at_abandon": 189.99,
    },
    {
        "session_id": "sess_demo_003",
        "event_count": 5,
        "max_stage": "cart",
        "first_seen": "2026-05-28T11:31:04Z",
        "last_seen": "2026-05-28T11:37:22Z",
        "converted": False,
        "funnel_collapse": True,
        "cart_value_at_abandon": 74.50,
    },
]

DEMO_RAW_EVENTS: list[dict[str, Any]] = [
    {
        "event_id": "evt_demo_001",
        "event_name": "homepage_viewed",
        "journey_stage": "acquisition",
        "session_id": "sess_demo_001",
        "channel": "paid_search",
        "occurred_at": "2026-05-28T09:10:00Z",
    },
    {
        "event_id": "evt_demo_002",
        "event_name": "payment_failed",
        "journey_stage": "checkout",
        "session_id": "sess_demo_002",
        "channel": "email",
        "occurred_at": "2026-05-28T10:16:05Z",
        "failure_reason": "issuer_declined",
        "cart_value": 189.99,
    },
]


def demo_dashboard_data() -> DashboardPayload:
    """Return self-contained demo data so the dashboard works without Docker."""
    return {
        "funnel": list(DEMO_FUNNEL),
        "revenue_leakage": list(DEMO_REVENUE_LEAKAGE),
        "experiments": list(DEMO_EXPERIMENTS),
        "sessions": list(DEMO_SESSIONS),
        "raw_events": list(DEMO_RAW_EVENTS),
        "metadata": {"source": "demo", "api_base_url": None},
    }


def read_raw_events(path: Path, limit: int = 200) -> list[dict[str, Any]]:
    """Read JSONL sample events for the raw explorer without requiring ClickHouse."""
    if not path.exists():
        return []

    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if len(events) >= limit:
                break
            stripped = line.strip()
            if not stripped:
                continue
            event = json.loads(stripped)
            events.append(_flatten_event(event))
    return events


def load_dashboard_data(
    api_base_url: str | None = None,
    sample_events_path: Path | None = None,
) -> DashboardPayload:
    """Load dashboard data from the local API when configured, otherwise demo/sample data.

    The optional API path keeps Streamlit separate from CI and lets reviewers run either a
    self-contained portfolio demo or point the dashboard at `make api-local`.
    """
    data = demo_dashboard_data()
    sample_path = sample_events_path or Path("data/sample_events.jsonl")
    raw_events = read_raw_events(sample_path)
    if raw_events:
        data["raw_events"] = raw_events

    if not api_base_url:
        return data

    clean_base_url = api_base_url.rstrip("/")
    try:
        data["funnel"] = _fetch_json(clean_base_url, "funnel")
        data["revenue_leakage"] = _fetch_json(clean_base_url, "revenue-leakage")
        data["experiments"] = _fetch_json(clean_base_url, "experiments")
        data["sessions"] = _fetch_json(clean_base_url, "sessions")
        data["metadata"] = {"source": "api", "api_base_url": clean_base_url}
    except (TimeoutError, URLError, json.JSONDecodeError, OSError) as exc:
        data["metadata"] = {
            "source": "demo_fallback",
            "api_base_url": clean_base_url,
            "warning": f"API unavailable; showing demo/sample data ({exc})",
        }
    return data


def executive_summary(payload: DashboardPayload) -> dict[str, float | int]:
    funnel = _records(payload, "funnel")
    leakage = _records(payload, "revenue_leakage")
    experiments = _records(payload, "experiments")
    sessions = _records(payload, "sessions")

    total_sessions = max((int(row.get("sessions", 0) or 0) for row in funnel), default=0)
    converted_sessions = sum(1 for row in sessions if bool(row.get("converted")))
    at_risk_revenue = sum(float(row.get("at_risk_revenue", 0) or 0) for row in leakage)
    best_experiment_rate = max(
        (float(row.get("conversion_rate", 0) or 0) for row in experiments),
        default=0.0,
    )
    return {
        "total_sessions": total_sessions,
        "converted_sessions_in_explorer": converted_sessions,
        "at_risk_revenue": round(at_risk_revenue, 2),
        "best_experiment_conversion_rate": round(best_experiment_rate, 4),
    }


def _fetch_json(base_url: str, path: str) -> list[dict[str, Any]]:
    with urlopen(f"{base_url}/{path}", timeout=3) as response:  # noqa: S310 - local demo URL
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise json.JSONDecodeError("expected a JSON list", str(payload), 0)
    return [dict(item) for item in payload]


def _flatten_event(event: dict[str, Any]) -> dict[str, Any]:
    properties = event.get("properties")
    flattened = {
        "event_id": event.get("event_id"),
        "event_name": event.get("event_name"),
        "journey_stage": event.get("journey_stage"),
        "session_id": event.get("session_id"),
        "customer_id": event.get("customer_id"),
        "anonymous_id": event.get("anonymous_id"),
        "channel": event.get("channel"),
        "occurred_at": event.get("occurred_at"),
    }
    if isinstance(properties, dict):
        for key in ("cart_value", "order_total", "experiment_id", "variant_id", "failure_reason"):
            if key in properties:
                flattened[key] = properties[key]
    return flattened


def _records(payload: DashboardPayload, key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]
