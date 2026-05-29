from datetime import UTC, datetime, timedelta
from random import Random
from uuid import uuid4

from customer_journey_intel.contracts.events import EcommerceEvent, EventName, JourneyStage


class JourneySimulator:
    """Generate deterministic synthetic ecommerce customer journeys."""

    def __init__(self, seed: int | None = None) -> None:
        self._random = Random(seed)

    @staticmethod
    def _customer_sequence(customer_id: str) -> int:
        try:
            return int(customer_id.rsplit("_", maxsplit=1)[-1])
        except ValueError:
            return 0

    def generate_journey(
        self,
        customer_id: str,
        started_at: datetime | None = None,
    ) -> list[EcommerceEvent]:
        current_time = started_at or datetime.now(tz=UTC)
        session_id = f"sess_{uuid4().hex[:12]}"
        anonymous_id = f"anon_{uuid4().hex[:12]}"
        customer_sequence = self._customer_sequence(customer_id)
        force_checkout_failure = customer_sequence > 0 and customer_sequence % 5 == 0
        experiment_id = (
            "checkout_cta" if customer_sequence > 0 and customer_sequence % 2 == 0 else None
        )
        variant_id = None
        if experiment_id:
            variant_id = "variant_b" if customer_sequence % 4 == 0 else "variant_a"
        events: list[EcommerceEvent] = []

        plan: list[tuple[EventName, JourneyStage, dict[str, object]]] = [
            (EventName.HOMEPAGE_VIEWED, JourneyStage.ACQUISITION, {"utm_source": "demo"}),
            (EventName.SEARCH_PERFORMED, JourneyStage.DISCOVERY, {"query": "running shoes"}),
        ]
        if experiment_id and variant_id:
            plan.extend(
                [
                    (
                        EventName.EXPERIMENT_ASSIGNED,
                        JourneyStage.DISCOVERY,
                        {"experiment_surface": "search_results"},
                    ),
                    (
                        EventName.VARIANT_EXPOSED,
                        JourneyStage.CONSIDERATION,
                        {"component": "checkout_cta", "copy": "free shipping"},
                    ),
                ]
            )
        plan.extend(
            [
                (
                    EventName.PRODUCT_VIEWED,
                    JourneyStage.CONSIDERATION,
                    {"product_id": "sku_1001", "price": 89.0},
                ),
                (
                    EventName.ADD_TO_CART,
                    JourneyStage.CART,
                    {"product_id": "sku_1001", "quantity": 1},
                ),
            ]
        )

        if force_checkout_failure or self._random.random() < 0.85:
            plan.append((EventName.CHECKOUT_STARTED, JourneyStage.CHECKOUT, {"cart_value": 89.0}))
            payment_succeeds = not force_checkout_failure and self._random.random() < 0.80
            if payment_succeeds:
                plan.extend(
                    [
                        (
                            EventName.SHIPPING_INFO_ADDED,
                            JourneyStage.CHECKOUT,
                            {"shipping_tier": "standard"},
                        ),
                        (
                            EventName.PAYMENT_ATTEMPTED,
                            JourneyStage.PAYMENT,
                            {"payment_method": "card"},
                        ),
                        (
                            EventName.PAYMENT_SUCCEEDED,
                            JourneyStage.PAYMENT,
                            {"amount": 89.0, "payment_method": "card"},
                        ),
                        (
                            EventName.ORDER_COMPLETED,
                            JourneyStage.RETENTION,
                            {"order_id": f"ord_{uuid4().hex[:8]}", "revenue": 89.0},
                        ),
                    ]
                )
            else:
                plan.extend(
                    [
                        (
                            EventName.PAYMENT_ATTEMPTED,
                            JourneyStage.PAYMENT,
                            {"payment_method": "card", "cart_value": 89.0},
                        ),
                        (
                            EventName.PAYMENT_FAILED,
                            JourneyStage.PAYMENT,
                            {
                                "failure_reason": "issuer_declined",
                                "cart_value": 89.0,
                                "payment_method": "card",
                            },
                        ),
                    ]
                )

        for event_name, journey_stage, properties in plan:
            events.append(
                EcommerceEvent(
                    event_id=uuid4(),
                    event_name=event_name,
                    occurred_at=current_time,
                    received_at=current_time + timedelta(seconds=self._random.randint(0, 4)),
                    customer_id=customer_id,
                    anonymous_id=anonymous_id,
                    session_id=session_id,
                    journey_stage=journey_stage,
                    channel="web",
                    experiment_id=experiment_id,
                    variant_id=variant_id,
                    properties=properties,
                )
            )
            current_time += timedelta(seconds=self._random.randint(5, 90))

        return events

    def generate_json_lines(self, journey_count: int) -> list[str]:
        lines: list[str] = []
        for index in range(journey_count):
            customer_id = f"cust_{index + 1:05d}"
            for event in self.generate_journey(customer_id=customer_id):
                lines.append(event.to_json_line())
        return lines
