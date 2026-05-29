from datetime import UTC, datetime

from customer_journey_intel.streaming.aggregates import (
    compute_experiment_batch,
    compute_funnel_batch,
    compute_revenue_events,
    compute_session_metrics,
    compute_session_row,
    extract_revenue_row,
)


def event(**overrides):
    base = {
        "event_id": "evt_1",
        "event_name": "product_viewed",
        "occurred_at": datetime(2026, 3, 1, 10, 2, tzinfo=UTC),
        "received_at": datetime(2026, 3, 1, 10, 2, 1, tzinfo=UTC),
        "customer_id": "cust_1",
        "anonymous_id": None,
        "session_id": "sess_1",
        "journey_stage": "consideration",
        "channel": "web",
        "properties": {"product_id": "sku_1", "price": 10.0},
    }
    base.update(overrides)
    return base


def test_funnel_batch_counts_events_and_sessions_by_stage():
    rows = compute_funnel_batch(
        [
            event(event_id="evt_1", session_id="sess_1"),
            event(event_id="evt_2", session_id="sess_2"),
        ],
        window_minutes=5,
    )

    assert rows[0]["event_count"] == 2
    assert rows[0]["session_count"] == 2
    assert rows[0]["window_start"] == datetime(2026, 3, 1, 10, 0, tzinfo=UTC)


def test_funnel_batch_splits_experiment_variants():
    rows = compute_funnel_batch(
        [
            event(event_id="evt_a", experiment_id="exp", variant_id="A"),
            event(event_id="evt_b", experiment_id="exp", variant_id="B"),
        ]
    )

    assert {row["variant_id"] for row in rows} == {"A", "B"}


def test_session_row_detects_conversion_and_highest_stage():
    rows = [
        event(
            event_name="checkout_started", journey_stage="checkout", properties={"cart_value": 25.0}
        ),
        event(
            event_id="evt_2",
            event_name="order_completed",
            journey_stage="retention",
            properties={"order_id": "ord_1", "revenue": 25.0},
        ),
    ]

    row = compute_session_row("sess_1", rows)

    assert row["max_journey_stage"] == "retention"
    assert row["converted"] == 1
    assert row["funnel_collapse"] == 0


def test_session_row_marks_funnel_collapse_and_cart_value_at_abandon():
    row = compute_session_row(
        "sess_1",
        [
            event(
                event_name="checkout_started",
                journey_stage="checkout",
                properties={"cart_value": 42.5},
            )
        ],
    )

    assert row["reached_checkout"] == 1
    assert row["converted"] == 0
    assert row["funnel_collapse"] == 1
    assert row["cart_value_at_abandon"] == 42.5


def test_compute_session_metrics_groups_by_session_id():
    rows = compute_session_metrics(
        [event(session_id="sess_a"), event(event_id="evt_2", session_id="sess_b")]
    )

    assert [row["session_id"] for row in rows] == ["sess_a", "sess_b"]


def test_extract_revenue_row_maps_payment_failure_properties():
    row = extract_revenue_row(
        event(
            event_name="payment_failed",
            journey_stage="payment",
            properties={
                "cart_value": 15.0,
                "payment_method": "visa",
                "failure_reason": "issuer_declined",
                "product_id": "sku_1",
            },
            experiment_id="exp_checkout",
            variant_id="B",
        )
    )

    assert row is not None
    assert row["cart_value"] == 15.0
    assert row["failure_reason"] == "issuer_declined"
    assert row["leakage"] == 1
    assert row["product_id"] == "sku_1"


def test_extract_revenue_row_ignores_non_revenue_event():
    assert extract_revenue_row(event(event_name="product_viewed")) is None


def test_compute_revenue_events_filters_revenue_taxonomy():
    rows = compute_revenue_events(
        [
            event(event_name="product_viewed"),
            event(
                event_id="evt_2",
                event_name="order_completed",
                journey_stage="retention",
                properties={"order_id": "ord_1", "revenue": 50.0},
            ),
        ]
    )

    assert len(rows) == 1
    assert rows[0]["event_name"] == "order_completed"


def test_experiment_batch_counts_assignment_exposure_and_conversion():
    rows = compute_experiment_batch(
        [
            event(
                event_name="experiment_assigned",
                journey_stage="acquisition",
                experiment_id="exp",
                variant_id="A",
            ),
            event(
                event_id="evt_2",
                event_name="variant_exposed",
                journey_stage="consideration",
                experiment_id="exp",
                variant_id="A",
            ),
            event(
                event_id="evt_3",
                event_name="order_completed",
                journey_stage="retention",
                experiment_id="exp",
                variant_id="A",
                occurred_at=datetime(2026, 3, 1, 10, 3, tzinfo=UTC),
            ),
            event(
                event_id="evt_4",
                event_name="product_viewed",
                occurred_at=datetime(2026, 3, 1, 10, 4, tzinfo=UTC),
            ),
        ],
        window_minutes=5,
    )

    assert rows == [
        {
            "window_start": datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
            "window_end": datetime(2026, 3, 1, 10, 5, tzinfo=UTC),
            "experiment_id": "exp",
            "variant_id": "A",
            "assigned_sessions": 1,
            "exposed_sessions": 1,
            "converted_sessions": 1,
        }
    ]
