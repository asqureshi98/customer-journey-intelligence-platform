from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from customer_journey_intel.contracts.data_quality import REVENUE_EVENTS
from customer_journey_intel.contracts.events import EventName, JourneyStage

FUNNEL_RANK = {
    JourneyStage.ACQUISITION.value: 1,
    JourneyStage.DISCOVERY.value: 2,
    JourneyStage.CONSIDERATION.value: 3,
    JourneyStage.CART.value: 4,
    JourneyStage.CHECKOUT.value: 5,
    JourneyStage.PAYMENT.value: 6,
    JourneyStage.RETENTION.value: 7,
    JourneyStage.RELIABILITY.value: 0,
}


def _properties(event: dict[str, Any]) -> dict[str, Any]:
    props = event.get("properties") or {}
    return props if isinstance(props, dict) else {}


def _float_property(event: dict[str, Any], *names: str) -> float | None:
    props = _properties(event)
    for name in names:
        value = props.get(name)
        if value is None or isinstance(value, bool):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _string_property(event: dict[str, Any], *names: str) -> str | None:
    props = _properties(event)
    for name in names:
        value = props.get(name)
        if value is not None and value != "":
            return str(value)
    return None


def _window_start(ts: datetime, window_minutes: int) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    minute = (ts.minute // window_minutes) * window_minutes
    return ts.replace(minute=minute, second=0, microsecond=0)


def compute_funnel_batch(
    events: list[dict[str, Any]], window_minutes: int = 5
) -> list[dict[str, Any]]:
    buckets: dict[tuple[Any, ...], dict[str, Any]] = {}
    sessions: defaultdict[tuple[Any, ...], set[str]] = defaultdict(set)
    for event in events:
        occurred_at = event["occurred_at"]
        window_start = _window_start(occurred_at, window_minutes)
        window_end = window_start + timedelta(minutes=window_minutes)
        key = (
            window_start,
            str(event["journey_stage"]),
            str(event["event_name"]),
            str(event.get("experiment_id") or "unattributed"),
            str(event.get("variant_id") or "unattributed"),
        )
        buckets.setdefault(
            key,
            {
                "window_start": window_start,
                "window_end": window_end,
                "journey_stage": key[1],
                "event_name": key[2],
                "session_count": 0,
                "event_count": 0,
                "experiment_id": key[3],
                "variant_id": key[4],
            },
        )["event_count"] += 1
        sessions[key].add(str(event["session_id"]))
    for key, row in buckets.items():
        row["session_count"] = len(sessions[key])
    return sorted(
        buckets.values(),
        key=lambda row: (row["window_start"], row["journey_stage"], row["event_name"]),
    )


def compute_session_metrics(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[str(event["session_id"])].append(event)
    return [
        compute_session_row(session_id, session_events)
        for session_id, session_events in sorted(grouped.items())
    ]


def compute_session_row(session_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(events, key=lambda event: event["occurred_at"])
    event_names = {str(event["event_name"]) for event in ordered}
    max_stage = max(
        (str(event["journey_stage"]) for event in ordered),
        key=lambda stage: FUNNEL_RANK.get(stage, -1),
    )
    reached_checkout = int(
        any(
            name in event_names
            for name in {EventName.CHECKOUT_STARTED.value, EventName.SHIPPING_INFO_ADDED.value}
        )
    )
    reached_payment = int(
        any(
            name in event_names
            for name in {
                EventName.PAYMENT_ATTEMPTED.value,
                EventName.PAYMENT_SUCCEEDED.value,
                EventName.PAYMENT_FAILED.value,
            }
        )
    )
    converted = int(EventName.ORDER_COMPLETED.value in event_names)
    cart_value_at_abandon = None
    if reached_checkout and not converted:
        checkout_values = [
            value
            for value in (
                _float_property(event, "cart_value", "cart_total", "amount", "revenue")
                for event in ordered
            )
            if value is not None
        ]
        cart_value_at_abandon = checkout_values[-1] if checkout_values else None
    first = ordered[0]
    return {
        "session_id": session_id,
        "customer_id": first.get("customer_id"),
        "anonymous_id": first.get("anonymous_id"),
        "channel": str(first.get("channel") or "unknown"),
        "first_seen": ordered[0]["occurred_at"],
        "last_seen": ordered[-1]["occurred_at"],
        "event_count": len(ordered),
        "max_journey_stage": max_stage,
        "reached_checkout": reached_checkout,
        "reached_payment": reached_payment,
        "converted": converted,
        "funnel_collapse": int(reached_checkout and not converted),
        "cart_value_at_abandon": cart_value_at_abandon,
    }


def extract_revenue_row(event: dict[str, Any]) -> dict[str, Any] | None:
    event_name = str(event.get("event_name") or "")
    if event_name not in REVENUE_EVENTS:
        return None
    cart_value = _float_property(event, "cart_value", "amount", "revenue", "cart_total")
    return {
        "event_id": str(event["event_id"]),
        "session_id": str(event["session_id"]),
        "customer_id": event.get("customer_id"),
        "event_name": event_name,
        "occurred_at": event["occurred_at"],
        "cart_value": cart_value,
        "product_id": _string_property(event, "product_id"),
        "order_id": _string_property(event, "order_id"),
        "payment_method": _string_property(event, "payment_method"),
        "failure_reason": _string_property(event, "failure_reason"),
        "leakage": int(event_name == EventName.PAYMENT_FAILED.value),
        "resolution": "failed"
        if event_name == EventName.PAYMENT_FAILED.value
        else "converted"
        if event_name == EventName.ORDER_COMPLETED.value
        else "pending",
        "experiment_id": str(event.get("experiment_id") or "unattributed"),
        "variant_id": str(event.get("variant_id") or "unattributed"),
    }


def compute_revenue_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for event in events if (row := extract_revenue_row(event)) is not None]


def compute_experiment_batch(
    events: list[dict[str, Any]], window_minutes: int = 5
) -> list[dict[str, Any]]:
    buckets: dict[tuple[datetime, str, str], dict[str, Any]] = {}
    assigned: defaultdict[tuple[datetime, str, str], set[str]] = defaultdict(set)
    exposed: defaultdict[tuple[datetime, str, str], set[str]] = defaultdict(set)
    converted: defaultdict[tuple[datetime, str, str], set[str]] = defaultdict(set)
    for event in events:
        experiment_id = event.get("experiment_id")
        variant_id = event.get("variant_id")
        if not experiment_id or not variant_id:
            continue
        window_start = _window_start(event["occurred_at"], window_minutes)
        key = (window_start, str(experiment_id), str(variant_id))
        buckets.setdefault(
            key,
            {
                "window_start": window_start,
                "window_end": window_start + timedelta(minutes=window_minutes),
                "experiment_id": str(experiment_id),
                "variant_id": str(variant_id),
                "assigned_sessions": 0,
                "exposed_sessions": 0,
                "converted_sessions": 0,
            },
        )
        session_id = str(event["session_id"])
        if event["event_name"] == EventName.EXPERIMENT_ASSIGNED.value:
            assigned[key].add(session_id)
        if event["event_name"] == EventName.VARIANT_EXPOSED.value:
            exposed[key].add(session_id)
        if event["event_name"] == EventName.ORDER_COMPLETED.value:
            converted[key].add(session_id)
    for key, row in buckets.items():
        row["assigned_sessions"] = len(assigned[key])
        row["exposed_sessions"] = len(exposed[key])
        row["converted_sessions"] = len(converted[key])
    return sorted(
        buckets.values(),
        key=lambda row: (row["window_start"], row["experiment_id"], row["variant_id"]),
    )
