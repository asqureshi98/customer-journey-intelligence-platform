"""Event deduplication helpers.

``deduplicate_event_dicts`` is a pure Python helper testable without Spark.
For Spark DataFrames use ``dropDuplicates`` as documented below.

Spark-level deduplication (within the watermark window)::

    from pyspark.sql.functions import col

    # Apply a 10-minute watermark on occurred_at first, then drop duplicates
    # within that window based on event_id.
    deduped = (
        projected
        .withWatermark("occurred_at", "10 minutes")
        .dropDuplicates(["event_id"])
    )

ClickHouse-level idempotency:
    ``funnel_metrics``, ``session_metrics``, and ``experiment_metrics`` all use
    ``ReplacingMergeTree`` so repeated inserts for the same primary key keep
    only the most-recent version.  ``raw_events`` uses plain ``MergeTree``; the
    application-layer dedup in ``deduplicate_event_dicts`` guards against
    exact duplicates arriving in the same micro-batch.
"""

from __future__ import annotations


def deduplicate_event_dicts(events: list[dict]) -> list[dict]:
    """Return a list with duplicate event_ids removed, keeping the first occurrence.

    Events missing an ``event_id`` are kept as-is (they will fail validation
    downstream and be routed to the DLQ).
    """
    seen: set[str] = set()
    result: list[dict] = []
    for event in events:
        eid = event.get("event_id")
        if eid is None:
            result.append(event)
            continue
        eid_str = str(eid)
        if eid_str not in seen:
            seen.add(eid_str)
            result.append(event)
    return result


def event_ids_in_batch(events: list[dict]) -> set[str]:
    """Return the set of event_ids present in a batch (for overlap detection)."""
    return {str(e["event_id"]) for e in events if e.get("event_id")}
