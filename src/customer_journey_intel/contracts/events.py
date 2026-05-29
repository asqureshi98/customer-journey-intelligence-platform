from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EventName(StrEnum):
    HOMEPAGE_VIEWED = "homepage_viewed"
    SEARCH_PERFORMED = "search_performed"
    CATEGORY_VIEWED = "category_viewed"
    PRODUCT_VIEWED = "product_viewed"
    ADD_TO_CART = "add_to_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    CHECKOUT_STARTED = "checkout_started"
    SHIPPING_INFO_ADDED = "shipping_info_added"
    PAYMENT_ATTEMPTED = "payment_attempted"
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"
    ORDER_COMPLETED = "order_completed"
    EXPERIMENT_ASSIGNED = "experiment_assigned"
    VARIANT_EXPOSED = "variant_exposed"
    PAGE_LOAD_SLOW = "page_load_slow"
    API_ERROR_SEEN = "api_error_seen"


class JourneyStage(StrEnum):
    ACQUISITION = "acquisition"
    DISCOVERY = "discovery"
    CONSIDERATION = "consideration"
    CART = "cart"
    CHECKOUT = "checkout"
    PAYMENT = "payment"
    RETENTION = "retention"
    RELIABILITY = "reliability"


class EcommerceEvent(BaseModel):
    """Pydantic data contract for one ecommerce customer journey event."""

    event_id: UUID
    event_name: EventName
    occurred_at: datetime
    received_at: datetime
    session_id: str = Field(min_length=1)
    journey_stage: JourneyStage
    channel: str = Field(min_length=1, examples=["web", "mobile", "email"])
    customer_id: str | None = None
    anonymous_id: str | None = None
    experiment_id: str | None = None
    variant_id: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=False)

    @model_validator(mode="after")
    def validate_business_rules(self) -> "EcommerceEvent":
        from customer_journey_intel.contracts.data_quality import validate_event_payload

        errors = validate_event_payload(self.model_dump())
        if errors:
            raise ValueError("; ".join(errors))
        return self

    def to_json_line(self) -> str:
        """Serialize as one JSON Lines record for Kafka/Redpanda seed data."""

        return self.model_dump_json()
