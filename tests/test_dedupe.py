"""Tests for batch-level event deduplication helpers.

All tests run without Docker or Spark.
"""

from __future__ import annotations

from customer_journey_intel.streaming.dedupe import deduplicate_event_dicts, event_ids_in_batch

# ── deduplicate_event_dicts ───────────────────────────────────────────────────


def test_deduplicate_removes_exact_duplicate_event_id():
    events = [
        {"event_id": "e1", "event_name": "homepage_viewed"},
        {"event_id": "e1", "event_name": "homepage_viewed"},
    ]
    result = deduplicate_event_dicts(events)
    assert len(result) == 1
    assert result[0]["event_id"] == "e1"


def test_deduplicate_keeps_first_occurrence():
    events = [
        {"event_id": "e1", "event_name": "first"},
        {"event_id": "e1", "event_name": "second"},
    ]
    result = deduplicate_event_dicts(events)
    assert result[0]["event_name"] == "first"


def test_deduplicate_preserves_unique_events():
    events = [
        {"event_id": "e1", "event_name": "homepage_viewed"},
        {"event_id": "e2", "event_name": "product_viewed"},
        {"event_id": "e3", "event_name": "add_to_cart"},
    ]
    result = deduplicate_event_dicts(events)
    assert len(result) == 3


def test_deduplicate_mixed_unique_and_duplicate():
    events = [
        {"event_id": "e1", "event_name": "a"},
        {"event_id": "e2", "event_name": "b"},
        {"event_id": "e1", "event_name": "a_dup"},
        {"event_id": "e3", "event_name": "c"},
    ]
    result = deduplicate_event_dicts(events)
    assert len(result) == 3
    ids = [e["event_id"] for e in result]
    assert ids == ["e1", "e2", "e3"]


def test_deduplicate_empty_list_returns_empty():
    assert deduplicate_event_dicts([]) == []


def test_deduplicate_keeps_events_without_event_id():
    events = [
        {"event_name": "bad_event_no_id"},
        {"event_id": "e1", "event_name": "good_event"},
    ]
    result = deduplicate_event_dicts(events)
    assert len(result) == 2


def test_deduplicate_single_event_is_unchanged():
    events = [{"event_id": "e1", "event_name": "homepage_viewed"}]
    result = deduplicate_event_dicts(events)
    assert result == events


# ── event_ids_in_batch ────────────────────────────────────────────────────────


def test_event_ids_in_batch_extracts_all_ids():
    events = [
        {"event_id": "e1", "event_name": "a"},
        {"event_id": "e2", "event_name": "b"},
    ]
    assert event_ids_in_batch(events) == {"e1", "e2"}


def test_event_ids_in_batch_ignores_missing_id():
    events = [
        {"event_name": "no_id"},
        {"event_id": "e1", "event_name": "has_id"},
    ]
    assert event_ids_in_batch(events) == {"e1"}


def test_event_ids_in_batch_returns_set_deduped():
    events = [{"event_id": "e1"}, {"event_id": "e1"}]
    assert event_ids_in_batch(events) == {"e1"}
