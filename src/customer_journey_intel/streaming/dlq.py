"""Dead-letter queue (DLQ) envelope helpers.

Events that fail JSON parsing or Pydantic validation are wrapped in a
``DLQEnvelope`` and serialised for quarantine.  All functions here are pure:
no Kafka or Spark dependency, so they are fully unit-testable.

To publish envelopes to the Redpanda DLQ topic wire this into a foreachBatch
sink::

    from customer_journey_intel.event_generator.producer import _make_producer
    from customer_journey_intel.streaming.dlq import make_dlq_envelope, serialize_dlq_envelope

    def dlq_sink(batch_df, batch_id):
        producer = _make_producer(bootstrap_servers)
        for row in batch_df.collect():
            env = make_dlq_envelope(
                raw_payload=row.raw_value,
                error_message=row.parse_error or "unknown",
                error_type=ErrorType.PARSE_ERROR,
            )
            producer.produce(
                topic="customer-events-dlq",
                key=env.event_id,
                value=serialize_dlq_envelope(env),
            )
        producer.flush()

The live Redpanda sink step is intentionally left for the team to wire up after
confirming the envelope schema fits the downstream quarantine consumer.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ErrorType(StrEnum):
    PARSE_ERROR = "parse_error"
    VALIDATION_ERROR = "validation_error"
    SCHEMA_ERROR = "schema_error"
    UNKNOWN = "unknown"


class DLQEnvelope(BaseModel):
    """Quarantine wrapper for events that cannot be processed."""

    envelope_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str
    raw_payload: str
    error_type: ErrorType
    error_message: str
    received_at: datetime
    dlq_enqueued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def make_dlq_envelope(
    raw_payload: str,
    error_message: str,
    error_type: ErrorType = ErrorType.UNKNOWN,
    event_id: str | None = None,
    received_at: datetime | None = None,
) -> DLQEnvelope:
    """Create a DLQ envelope for a failed event.

    ``event_id`` defaults to a fresh UUID when it cannot be extracted from the
    raw payload (e.g. parse failure).  ``received_at`` defaults to now.
    """
    return DLQEnvelope(
        event_id=event_id or str(uuid.uuid4()),
        raw_payload=raw_payload,
        error_type=error_type,
        error_message=error_message,
        received_at=received_at or datetime.now(UTC),
    )


def serialize_dlq_envelope(envelope: DLQEnvelope) -> str:
    """Serialise a DLQ envelope to a compact JSON string for Kafka publish."""
    return envelope.model_dump_json()


def parse_event_id_from_payload(raw_payload: str) -> str | None:
    """Best-effort extraction of event_id from a raw JSON string.

    Returns ``None`` if the payload is not valid JSON or lacks event_id.
    """
    try:
        data = json.loads(raw_payload)
        eid = data.get("event_id")
        return str(eid) if eid else None
    except (json.JSONDecodeError, AttributeError):
        return None
