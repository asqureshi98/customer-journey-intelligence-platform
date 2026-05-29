from __future__ import annotations

from datetime import datetime
from typing import Any

from customer_journey_intel.contracts.events import EventName, JourneyStage

EVENT_STAGE_COMPATIBILITY: dict[str, set[str]] = {
    EventName.HOMEPAGE_VIEWED.value: {JourneyStage.ACQUISITION.value},
    EventName.SEARCH_PERFORMED.value: {JourneyStage.DISCOVERY.value},
    EventName.CATEGORY_VIEWED.value: {JourneyStage.DISCOVERY.value},
    EventName.PRODUCT_VIEWED.value: {
        JourneyStage.DISCOVERY.value,
        JourneyStage.CONSIDERATION.value,
    },
    EventName.ADD_TO_CART.value: {JourneyStage.CART.value},
    EventName.REMOVE_FROM_CART.value: {JourneyStage.CART.value},
    EventName.CHECKOUT_STARTED.value: {JourneyStage.CHECKOUT.value},
    EventName.SHIPPING_INFO_ADDED.value: {JourneyStage.CHECKOUT.value},
    EventName.PAYMENT_ATTEMPTED.value: {JourneyStage.PAYMENT.value},
    EventName.PAYMENT_SUCCEEDED.value: {JourneyStage.PAYMENT.value},
    EventName.PAYMENT_FAILED.value: {JourneyStage.PAYMENT.value},
    EventName.ORDER_COMPLETED.value: {JourneyStage.RETENTION.value},
    EventName.EXPERIMENT_ASSIGNED.value: {
        JourneyStage.ACQUISITION.value,
        JourneyStage.DISCOVERY.value,
    },
    EventName.VARIANT_EXPOSED.value: {JourneyStage.CONSIDERATION.value},
    EventName.PAGE_LOAD_SLOW.value: {JourneyStage.RELIABILITY.value},
    EventName.API_ERROR_SEEN.value: {JourneyStage.RELIABILITY.value},
}

REVENUE_EVENTS = {
    EventName.PAYMENT_ATTEMPTED.value,
    EventName.PAYMENT_SUCCEEDED.value,
    EventName.PAYMENT_FAILED.value,
    EventName.ORDER_COMPLETED.value,
}
PAYMENT_EVENTS = {
    EventName.PAYMENT_ATTEMPTED.value,
    EventName.PAYMENT_SUCCEEDED.value,
    EventName.PAYMENT_FAILED.value,
}


def _present(value: Any) -> bool:
    return value is not None and value != ""


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate_event_payload(row: dict[str, Any]) -> list[str]:
    """Return human-readable data-quality violations for one event-like dict."""

    errors: list[str] = []
    event_name = str(row.get("event_name") or "")
    journey_stage = str(row.get("journey_stage") or "")
    properties = row.get("properties") or {}
    if not isinstance(properties, dict):
        errors.append("properties must be an object")
        properties = {}

    if not _present(row.get("customer_id")) and not _present(row.get("anonymous_id")):
        errors.append("At least one customer identity is required: customer_id or anonymous_id")

    allowed_stages = EVENT_STAGE_COMPATIBILITY.get(event_name)
    if allowed_stages is None:
        errors.append(f"unknown event_name: {event_name}")
    elif journey_stage not in allowed_stages:
        errors.append(f"event {event_name} is not compatible with journey_stage {journey_stage}")

    occurred_at = row.get("occurred_at")
    received_at = row.get("received_at")
    if (
        isinstance(occurred_at, datetime)
        and isinstance(received_at, datetime)
        and occurred_at > received_at
    ):
        errors.append("occurred_at must be before or equal to received_at")

    for key in ("cart_value", "amount", "revenue", "price", "unit_price"):
        if key in properties:
            amount = _as_float(properties.get(key))
            if amount is None:
                errors.append(f"{key} must be numeric")
            elif amount < 0:
                errors.append(f"{key} must be non-negative")

    if _present(row.get("experiment_id")) != _present(row.get("variant_id")):
        errors.append("experiment_id and variant_id must be present together")
    if event_name in {
        EventName.EXPERIMENT_ASSIGNED.value,
        EventName.VARIANT_EXPOSED.value,
    } and (not _present(row.get("experiment_id")) or not _present(row.get("variant_id"))):
        errors.append(f"{event_name} requires experiment_id and variant_id")

    if event_name in PAYMENT_EVENTS and not _present(properties.get("payment_method")):
        errors.append(f"{event_name} requires properties.payment_method")
    if event_name == EventName.PAYMENT_FAILED.value and not _present(
        properties.get("failure_reason")
    ):
        errors.append("payment_failed requires properties.failure_reason")
    if event_name == EventName.ORDER_COMPLETED.value and not _present(properties.get("order_id")):
        errors.append("order_completed requires properties.order_id")

    return errors


def validate_session_metrics_row(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not _present(row.get("session_id")):
        errors.append("session_id is required")
    if row.get("event_count", 0) < 0:
        errors.append("event_count must be non-negative")
    first_seen = row.get("first_seen")
    last_seen = row.get("last_seen")
    if (
        isinstance(first_seen, datetime)
        and isinstance(last_seen, datetime)
        and first_seen > last_seen
    ):
        errors.append("first_seen must be before or equal to last_seen")
    if row.get("funnel_collapse") and not row.get("reached_checkout"):
        errors.append("funnel_collapse requires reached_checkout")
    cart_value = _as_float(row.get("cart_value_at_abandon"))
    if cart_value is not None and cart_value < 0:
        errors.append("cart_value_at_abandon must be non-negative")
    return errors


def validate_revenue_metrics_row(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if row.get("event_name") not in REVENUE_EVENTS:
        errors.append("event_name must be revenue-relevant")
    cart_value = _as_float(row.get("cart_value"))
    if cart_value is not None and cart_value < 0:
        errors.append("cart_value must be non-negative")
    if row.get("event_name") in PAYMENT_EVENTS and not _present(row.get("payment_method")):
        errors.append("payment_method is required for payment events")
    if row.get("event_name") == EventName.PAYMENT_FAILED.value and not _present(
        row.get("failure_reason")
    ):
        errors.append("failure_reason is required for failed payments")
    return errors
