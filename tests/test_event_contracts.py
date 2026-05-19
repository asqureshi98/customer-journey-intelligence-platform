from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from customer_journey_intel.contracts.events import EcommerceEvent, EventName


def test_ecommerce_event_accepts_customer_journey_payload():
    event = EcommerceEvent(
        event_id="018f4dd7-9a18-7c7a-b201-1f6d26cdd111",
        event_name=EventName.PRODUCT_VIEWED,
        occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        received_at=datetime(2026, 1, 1, 12, 0, 2, tzinfo=UTC),
        customer_id="cust_123",
        anonymous_id="anon_123",
        session_id="sess_123",
        journey_stage="consideration",
        channel="web",
        properties={"product_id": "sku_1", "price": 49.99},
    )

    assert isinstance(event.event_id, UUID)
    assert event.event_name == EventName.PRODUCT_VIEWED
    assert event.properties["product_id"] == "sku_1"


def test_ecommerce_event_rejects_missing_identity():
    with pytest.raises(ValidationError) as exc_info:
        EcommerceEvent(
            event_id="018f4dd7-9a18-7c7a-b201-1f6d26cdd111",
            event_name=EventName.CHECKOUT_STARTED,
            occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            received_at=datetime(2026, 1, 1, 12, 0, 2, tzinfo=UTC),
            session_id="sess_123",
            journey_stage="checkout",
            channel="web",
            properties={},
        )

    assert "At least one customer identity" in str(exc_info.value)


def test_ecommerce_event_rejects_unknown_journey_stage():
    with pytest.raises(ValidationError) as exc_info:
        EcommerceEvent(
            event_id="018f4dd7-9a18-7c7a-b201-1f6d26cdd111",
            event_name=EventName.CHECKOUT_STARTED,
            occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            received_at=datetime(2026, 1, 1, 12, 0, 2, tzinfo=UTC),
            customer_id="cust_123",
            session_id="sess_123",
            journey_stage="not-a-real-stage",
            channel="web",
            properties={},
        )

    message = str(exc_info.value)
    assert "Input should be" in message or "not-a-real-stage" in message
