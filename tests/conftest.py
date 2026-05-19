"""
Shared pytest fixtures for the Customer Journey Intelligence Platform test suite.

All fixtures in this file are available to every test module without import.
No Docker or external services are required to use these fixtures.
"""

from datetime import UTC, datetime

import pytest


@pytest.fixture()
def sample_event_dict() -> dict:
    """Return a minimal valid EcommerceEvent payload as a plain dictionary.

    This fixture is the canonical test baseline. Tests that need a valid event
    but do not care about specific field values should use this rather than
    duplicating boilerplate construction.
    """
    return {
        "event_id": "018f4dd7-9a18-7c7a-b201-1f6d26cdd001",
        "event_name": "product_viewed",
        "occurred_at": datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC),
        "received_at": datetime(2026, 3, 1, 10, 0, 2, tzinfo=UTC),
        "customer_id": "cust_fixture_001",
        "anonymous_id": None,
        "session_id": "sess_fixture_abc123",
        "journey_stage": "consideration",
        "channel": "web",
        "properties": {
            "product_id": "sku_999",
            "product_name": "Trail Running Shoe",
            "price": 129.99,
            "currency": "USD",
            "category": "footwear",
        },
    }


@pytest.fixture()
def checkout_event_dict() -> dict:
    """Return a valid checkout_started event payload."""
    return {
        "event_id": "018f4dd7-9a18-7c7a-b201-1f6d26cdd002",
        "event_name": "checkout_started",
        "occurred_at": datetime(2026, 3, 1, 10, 5, 0, tzinfo=UTC),
        "received_at": datetime(2026, 3, 1, 10, 5, 1, tzinfo=UTC),
        "customer_id": "cust_fixture_001",
        "anonymous_id": None,
        "session_id": "sess_fixture_abc123",
        "journey_stage": "checkout",
        "channel": "web",
        "properties": {
            "cart_value": 129.99,
            "item_count": 1,
            "currency": "USD",
        },
    }


@pytest.fixture()
def payment_failed_event_dict() -> dict:
    """Return a valid payment_failed event payload for revenue leakage tests."""
    return {
        "event_id": "018f4dd7-9a18-7c7a-b201-1f6d26cdd003",
        "event_name": "payment_failed",
        "occurred_at": datetime(2026, 3, 1, 10, 7, 30, tzinfo=UTC),
        "received_at": datetime(2026, 3, 1, 10, 7, 31, tzinfo=UTC),
        "customer_id": "cust_fixture_001",
        "anonymous_id": None,
        "session_id": "sess_fixture_abc123",
        "journey_stage": "payment",
        "channel": "web",
        "properties": {
            "failure_reason": "issuer_declined",
            "payment_method": "visa",
            "cart_value": 129.99,
            "currency": "USD",
        },
    }


@pytest.fixture()
def experiment_event_dict() -> dict:
    """Return a valid experiment_assigned event payload."""
    return {
        "event_id": "018f4dd7-9a18-7c7a-b201-1f6d26cdd004",
        "event_name": "experiment_assigned",
        "occurred_at": datetime(2026, 3, 1, 10, 0, 1, tzinfo=UTC),
        "received_at": datetime(2026, 3, 1, 10, 0, 2, tzinfo=UTC),
        "customer_id": "cust_fixture_001",
        "anonymous_id": None,
        "session_id": "sess_fixture_abc123",
        "journey_stage": "discovery",
        "channel": "web",
        "experiment_id": "exp_checkout_cta_v2",
        "variant_id": "variant_b",
        "properties": {
            "experiment_name": "Checkout CTA Button Copy",
            "variant_name": "Add to Bag",
            "allocation_pct": 50,
        },
    }
