import json
from datetime import UTC, datetime

from customer_journey_intel.contracts.events import JourneyStage
from customer_journey_intel.event_generator.simulator import JourneySimulator


def test_journey_simulator_emits_ordered_customer_story_with_required_events():
    simulator = JourneySimulator(seed=42)
    events = simulator.generate_journey(
        customer_id="cust_42", started_at=datetime(2026, 1, 1, tzinfo=UTC)
    )

    event_names = [event.event_name.value for event in events]

    assert event_names[0] == "homepage_viewed"
    assert events[0].journey_stage == JourneyStage.ACQUISITION
    assert "product_viewed" in event_names
    assert any(
        name in event_names for name in ["order_completed", "payment_failed", "checkout_started"]
    )
    assert all(event.customer_id == "cust_42" for event in events)
    assert all(event.session_id == events[0].session_id for event in events)
    assert [event.occurred_at for event in events] == sorted(event.occurred_at for event in events)


def test_journey_simulator_sets_homepage_viewed_to_acquisition_stage():
    simulator = JourneySimulator(seed=1)

    first_event = simulator.generate_journey(
        customer_id="cust_stage", started_at=datetime(2026, 1, 1, tzinfo=UTC)
    )[0]

    assert first_event.event_name.value == "homepage_viewed"
    assert first_event.journey_stage == JourneyStage.ACQUISITION


def test_journey_simulator_can_render_json_lines_for_redpanda_seed_data():
    simulator = JourneySimulator(seed=7)

    lines = simulator.generate_json_lines(journey_count=2)

    assert len(lines) >= 4
    assert all('"event_name"' in line for line in lines)
    assert all('"journey_stage"' in line for line in lines)


def test_default_sample_includes_revenue_leakage_and_experiment_events():
    simulator = JourneySimulator(seed=42)

    events = [json.loads(line) for line in simulator.generate_json_lines(journey_count=5)]
    event_names = {event["event_name"] for event in events}

    assert "payment_failed" in event_names
    assert "experiment_assigned" in event_names
    assert "variant_exposed" in event_names
