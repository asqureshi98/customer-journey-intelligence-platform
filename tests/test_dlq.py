"""Tests for DLQ envelope creation and serialisation.

All tests run without Docker, Kafka, or Spark.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from customer_journey_intel.streaming.dlq import (
    DLQEnvelope,
    ErrorType,
    make_dlq_envelope,
    parse_event_id_from_payload,
    serialize_dlq_envelope,
)

# ── make_dlq_envelope ─────────────────────────────────────────────────────────


def test_make_dlq_envelope_returns_dlq_envelope_instance():
    env = make_dlq_envelope(
        raw_payload='{"bad": "json"',
        error_message="Unexpected end of JSON",
        error_type=ErrorType.PARSE_ERROR,
    )
    assert isinstance(env, DLQEnvelope)


def test_make_dlq_envelope_sets_error_fields():
    env = make_dlq_envelope(
        raw_payload="garbage",
        error_message="Schema mismatch",
        error_type=ErrorType.SCHEMA_ERROR,
    )
    assert env.error_type == ErrorType.SCHEMA_ERROR
    assert env.error_message == "Schema mismatch"
    assert env.raw_payload == "garbage"


def test_make_dlq_envelope_generates_event_id_when_not_provided():
    env = make_dlq_envelope(raw_payload="{}", error_message="missing event_id")
    assert env.event_id
    assert len(env.event_id) == 36  # UUID string length


def test_make_dlq_envelope_uses_provided_event_id():
    env = make_dlq_envelope(
        raw_payload="{}",
        error_message="validation failed",
        event_id="abc-123",
    )
    assert env.event_id == "abc-123"


def test_make_dlq_envelope_sets_received_at_when_provided():
    ts = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    env = make_dlq_envelope(raw_payload="{}", error_message="err", received_at=ts)
    assert env.received_at == ts


def test_make_dlq_envelope_defaults_received_at_to_now():
    before = datetime.now(UTC)
    env = make_dlq_envelope(raw_payload="{}", error_message="err")
    after = datetime.now(UTC)
    assert before <= env.received_at <= after


def test_make_dlq_envelope_defaults_error_type_to_unknown():
    env = make_dlq_envelope(raw_payload="{}", error_message="unknown problem")
    assert env.error_type == ErrorType.UNKNOWN


# ── serialize_dlq_envelope ────────────────────────────────────────────────────


def test_serialize_dlq_envelope_produces_valid_json():
    env = make_dlq_envelope(raw_payload="{}", error_message="test error")
    json_str = serialize_dlq_envelope(env)
    parsed = json.loads(json_str)
    assert "event_id" in parsed
    assert "error_message" in parsed
    assert "raw_payload" in parsed
    assert "error_type" in parsed
    assert "dlq_enqueued_at" in parsed


def test_serialize_dlq_envelope_is_string():
    env = make_dlq_envelope(raw_payload="{}", error_message="err")
    assert isinstance(serialize_dlq_envelope(env), str)


def test_serialize_dlq_envelope_round_trips_error_type():
    env = make_dlq_envelope(
        raw_payload="{}", error_message="err", error_type=ErrorType.VALIDATION_ERROR
    )
    parsed = json.loads(serialize_dlq_envelope(env))
    assert parsed["error_type"] == "validation_error"


# ── parse_event_id_from_payload ───────────────────────────────────────────────


def test_parse_event_id_from_valid_payload():
    payload = '{"event_id": "evt-abc", "event_name": "homepage_viewed"}'
    assert parse_event_id_from_payload(payload) == "evt-abc"


def test_parse_event_id_returns_none_for_invalid_json():
    assert parse_event_id_from_payload("not json at all") is None


def test_parse_event_id_returns_none_when_field_missing():
    assert parse_event_id_from_payload('{"event_name": "homepage_viewed"}') is None


def test_parse_event_id_returns_none_for_null_event_id():
    assert parse_event_id_from_payload('{"event_id": null}') is None
