from datetime import UTC, datetime, timedelta

from customer_journey_intel.contracts.data_quality import (
    validate_event_payload,
    validate_revenue_metrics_row,
    validate_session_metrics_row,
)


def test_event_payload_rejects_incompatible_event_stage(sample_event_dict):
    sample_event_dict["event_name"] = "payment_failed"
    sample_event_dict["journey_stage"] = "discovery"
    sample_event_dict["properties"] = {
        "payment_method": "visa",
        "failure_reason": "issuer_declined",
        "cart_value": 99.0,
    }

    assert "not compatible" in "; ".join(validate_event_payload(sample_event_dict))


def test_event_payload_rejects_timestamp_ordering(sample_event_dict):
    sample_event_dict["occurred_at"] = datetime(2026, 3, 1, 10, 1, tzinfo=UTC)
    sample_event_dict["received_at"] = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)

    assert "occurred_at" in "; ".join(validate_event_payload(sample_event_dict))


def test_event_payload_rejects_negative_monetary_property(checkout_event_dict):
    checkout_event_dict["properties"]["cart_value"] = -1

    assert "cart_value must be non-negative" in validate_event_payload(checkout_event_dict)


def test_event_payload_rejects_experiment_without_variant(sample_event_dict):
    sample_event_dict["experiment_id"] = "exp_checkout"

    assert "experiment_id and variant_id" in "; ".join(validate_event_payload(sample_event_dict))


def test_event_payload_rejects_payment_event_without_payment_method(payment_failed_event_dict):
    del payment_failed_event_dict["properties"]["payment_method"]

    assert "payment_method" in "; ".join(validate_event_payload(payment_failed_event_dict))


def test_session_metrics_rejects_first_seen_after_last_seen():
    errors = validate_session_metrics_row(
        {
            "session_id": "sess_1",
            "event_count": 2,
            "first_seen": datetime(2026, 3, 1, 10, 5, tzinfo=UTC),
            "last_seen": datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        }
    )

    assert "first_seen" in "; ".join(errors)


def test_session_metrics_rejects_invalid_funnel_collapse():
    errors = validate_session_metrics_row(
        {
            "session_id": "sess_1",
            "event_count": 1,
            "first_seen": datetime.now(tz=UTC),
            "last_seen": datetime.now(tz=UTC) + timedelta(seconds=1),
            "funnel_collapse": 1,
            "reached_checkout": 0,
        }
    )

    assert "funnel_collapse" in "; ".join(errors)


def test_revenue_metrics_rejects_negative_cart_value():
    errors = validate_revenue_metrics_row(
        {
            "event_name": "payment_failed",
            "cart_value": -10.0,
            "payment_method": "visa",
            "failure_reason": "issuer_declined",
        }
    )

    assert "cart_value must be non-negative" in errors
