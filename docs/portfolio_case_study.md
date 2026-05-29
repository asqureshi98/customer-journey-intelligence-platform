# Portfolio case study: Customer journey intelligence

## Problem

Ecommerce teams often know total orders and total traffic, but they struggle to connect individual journey friction to revenue impact. A product manager may ask whether checkout copy improved conversion, an engineering manager may ask whether API errors correlate with cart abandonment, and a finance stakeholder may ask how much revenue is at risk from payment failures.

This project demonstrates a local data platform that answers those questions from an event stream while remaining small enough for a reviewer to run on a laptop.

## Solution overview

The platform generates synthetic customer journeys, validates their event contracts, streams them through Redpanda and Spark, stores an idempotent raw event trail in ClickHouse, and exposes analytics through FastAPI and an optional Streamlit dashboard.

The design separates four concerns:

1. **Event truth** — Pydantic contracts and raw ClickHouse storage preserve the source facts.
2. **Streaming reliability** — Spark parsing, invalid-row split, watermarking, dedupe, and checkpointed writes protect the pipeline from malformed and replayed data.
3. **Analytical marts** — funnel, session, revenue, and experiment models define dashboard-ready grains.
4. **Reviewer surfaces** — FastAPI and Streamlit make the business story visible without requiring a separate BI tool.

## Business questions answered

| Question | Current answer path |
|---|---|
| Where does the funnel lose users? | `/funnel`, funnel dashboard, `funnel_metrics` schema/helper. |
| Which sessions reached checkout but failed to convert? | `/sessions`, session explorer, `session_metrics` schema/helper. |
| How much revenue is at risk from failed payments? | `/revenue-leakage`, revenue leakage dashboard, `revenue_events` schema/helper. |
| Which experiment variant converts better? | `/experiments`, experiment dashboard, `experiment_metrics` schema/helper. |
| Can we audit the raw events behind a metric? | `raw_events`, JSONL samples, dashboard raw/session explorer. |

## Example API outputs

`GET /health`

```json
{"status": "ok", "service": "customer-journey-intel"}
```

`GET /funnel`

```json
[
  {
    "journey_stage": "cart",
    "event_name": "add_to_cart",
    "event_count": 31,
    "sessions": 29,
    "conversion_rate": 0.58
  }
]
```

`GET /sessions`

```json
[
  {
    "session_id": "sess_001",
    "event_count": 7,
    "max_stage": "payment",
    "first_seen": "2026-01-01T12:00:00Z",
    "last_seen": "2026-01-01T12:04:12Z",
    "converted": false,
    "funnel_collapse": true,
    "cart_value_at_abandon": 145.98
  }
]
```

`GET /revenue-leakage`

```json
[
  {
    "failure_reason": "issuer_declined",
    "failed_payments": 7,
    "at_risk_revenue": 932.41,
    "affected_sessions": 7
  }
]
```

`GET /experiments`

```json
[
  {
    "experiment_id": "checkout_cta",
    "variant_id": "variant_b",
    "assigned_sessions": 120,
    "exposed_sessions": 114,
    "converted_sessions": 31,
    "conversion_rate": 0.27
  }
]
```

The examples show response shapes, not fixed benchmark results. Local values depend on generated sample data and whether the API is reading ClickHouse or the dashboard is using fallback data.

## Dashboard narrative

The Streamlit dashboard is intended as a reviewer walkthrough:

- Executive overview: sessions, conversions, at-risk revenue, and best experiment conversion rate.
- Funnel analysis: drop-off by event/stage.
- Revenue leakage: failed payment reasons ranked by at-risk revenue.
- Experiment performance: assignment/exposure/conversion by variant.
- Raw/session explorer: inspect journey-level rows behind aggregates.

Screenshots are not committed from this environment. `docs/dashboard.md` explains how to capture local screenshots under `docs/assets/dashboard/` if desired.

## Engineering decisions worth discussing

- Redpanda keeps the architecture Kafka-compatible but lightweight for local development.
- ClickHouse is a good fit for low-latency analytical reads over event and metric tables.
- Pydantic contracts make bad event examples explicit and testable.
- Spark is used where event-time dedupe, watermarking, and future stateful metrics belong; pure-Python helpers keep current aggregate logic unit-testable.
- The README and roadmap clearly separate implemented local features from production roadmap features.

## Current limitations

- The project uses synthetic data only.
- Analytical mart tables are defined and helper logic exists, but continuous Spark writers into every mart are not complete.
- DLQ envelope creation is tested, but live Spark publishing to the DLQ topic is not complete.
- Streamlit is a portfolio dashboard, not an authenticated BI deployment.
- No cloud orchestration, managed monitoring, or alert delivery is included.
