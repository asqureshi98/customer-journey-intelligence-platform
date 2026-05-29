# Data Model — Realtime Customer Journey Intelligence Platform

## Core Event Envelope

Every event emitted by the journey simulator and consumed by the streaming job shares
the following envelope fields. This schema is enforced by the `EcommerceEvent` Pydantic
model in `src/customer_journey_intel/contracts/events.py`.

| Field          | Type                    | Nullable | Description                                                     |
|----------------|-------------------------|----------|-----------------------------------------------------------------|
| `event_id`     | UUID                    | No       | Globally unique event identifier (UUIDv7 recommended)          |
| `event_name`   | EventName (StrEnum)     | No       | Controlled vocabulary — see taxonomy below                     |
| `occurred_at`  | datetime (UTC)          | No       | Client-side event timestamp (used for Spark watermarking)      |
| `received_at`  | datetime (UTC)          | No       | Platform ingestion time; delta vs `occurred_at` = late latency |
| `customer_id`  | str                     | Yes      | Authenticated user identifier                                  |
| `anonymous_id` | str                     | Yes      | Pre-auth / cookie-based identity                               |
| `session_id`   | str                     | No       | Session / funnel grouping key; Kafka partition key             |
| `journey_stage`| JourneyStage (StrEnum)  | No       | Business funnel stage — see stages below                       |
| `channel`      | str                     | No       | Source channel: `web`, `mobile`, `email`, `push`               |
| `experiment_id`| str                     | Yes      | Active A/B experiment identifier                               |
| `variant_id`   | str                     | Yes      | Assigned experiment variant                                    |
| `properties`   | dict[str, Any]          | No       | Event-type-specific payload — see per-event schemas below      |

Identity constraint: at least one of `customer_id` or `anonymous_id` must be present.
This is enforced by a Pydantic `model_validator`.

## Journey Stage Taxonomy

| Stage          | Events that set this stage                                             |
|----------------|------------------------------------------------------------------------|
| `acquisition`  | `homepage_viewed` (direct or paid traffic landing)                    |
| `discovery`    | `search_performed`, `category_viewed`, `product_viewed`               |
| `consideration`| `product_viewed` (repeated), `variant_exposed`                        |
| `cart`         | `add_to_cart`, `remove_from_cart`                                     |
| `checkout`     | `checkout_started`, `shipping_info_added`                             |
| `payment`      | `payment_attempted`, `payment_succeeded`, `payment_failed`            |
| `retention`    | `order_completed`                                                     |
| `reliability`  | `page_load_slow`, `api_error_seen`                                    |

## Event Taxonomy — All 16 Event Types

### homepage_viewed
Customer lands on the homepage. Always the first event in a new session.

```json
{
  "event_name": "homepage_viewed",
  "journey_stage": "acquisition",
  "properties": {
    "utm_source": "google",
    "utm_medium": "cpc",
    "utm_campaign": "spring_sale_2026",
    "referrer": "https://google.com/search?q=running+shoes",
    "page_load_ms": 1240
  }
}
```

### search_performed
Free-text or faceted product search.

```json
{
  "event_name": "search_performed",
  "journey_stage": "discovery",
  "properties": {
    "query": "waterproof trail running shoes",
    "result_count": 42,
    "filters_applied": ["brand:Salomon", "price:0-150"],
    "search_type": "text"
  }
}
```

### category_viewed
Category or collection page loaded.

```json
{
  "event_name": "category_viewed",
  "journey_stage": "discovery",
  "properties": {
    "category_id": "cat_trail_running",
    "category_name": "Trail Running",
    "product_count": 87,
    "sort_order": "relevance"
  }
}
```

### product_viewed
Product detail page opened.

```json
{
  "event_name": "product_viewed",
  "journey_stage": "consideration",
  "properties": {
    "product_id": "sku_1001",
    "product_name": "Speedcross 6 Trail Shoe",
    "brand": "Salomon",
    "price": 139.99,
    "currency": "USD",
    "category": "trail_running",
    "in_stock": true,
    "image_url": "https://cdn.example.com/sku_1001.jpg"
  }
}
```

### add_to_cart
Item added to the shopping cart.

```json
{
  "event_name": "add_to_cart",
  "journey_stage": "cart",
  "properties": {
    "product_id": "sku_1001",
    "product_name": "Speedcross 6 Trail Shoe",
    "quantity": 1,
    "unit_price": 139.99,
    "cart_total": 139.99,
    "currency": "USD"
  }
}
```

### remove_from_cart
Item removed from the cart (hesitation signal).

```json
{
  "event_name": "remove_from_cart",
  "journey_stage": "cart",
  "properties": {
    "product_id": "sku_1001",
    "quantity": 1,
    "cart_total_after": 0.0,
    "removal_reason": "size_unavailable"
  }
}
```

### checkout_started
Customer enters the checkout flow.

```json
{
  "event_name": "checkout_started",
  "journey_stage": "checkout",
  "properties": {
    "cart_value": 139.99,
    "item_count": 1,
    "currency": "USD",
    "coupon_applied": false
  }
}
```

### shipping_info_added
Delivery address and shipping method confirmed.

```json
{
  "event_name": "shipping_info_added",
  "journey_stage": "checkout",
  "properties": {
    "shipping_tier": "standard",
    "shipping_cost": 5.99,
    "estimated_delivery_days": 5,
    "country": "US",
    "state": "CO"
  }
}
```

### payment_attempted
Payment form submitted to gateway.

```json
{
  "event_name": "payment_attempted",
  "journey_stage": "payment",
  "properties": {
    "payment_method": "visa",
    "cart_value": 145.98,
    "currency": "USD",
    "gateway": "stripe"
  }
}
```

### payment_succeeded
Payment gateway returned success.

```json
{
  "event_name": "payment_succeeded",
  "journey_stage": "payment",
  "properties": {
    "payment_method": "visa",
    "amount": 145.98,
    "currency": "USD",
    "gateway_transaction_id": "pi_3P8xYZ2e"
  }
}
```

### payment_failed
Payment gateway returned a failure code.

```json
{
  "event_name": "payment_failed",
  "journey_stage": "payment",
  "properties": {
    "failure_reason": "issuer_declined",
    "payment_method": "visa",
    "cart_value": 145.98,
    "currency": "USD",
    "error_code": "card_declined",
    "gateway": "stripe"
  }
}
```

### order_completed
Order confirmed and fulfillment triggered.

```json
{
  "event_name": "order_completed",
  "journey_stage": "retention",
  "properties": {
    "order_id": "ord_a1b2c3d4",
    "revenue": 145.98,
    "currency": "USD",
    "item_count": 1,
    "coupon_code": null
  }
}
```

### experiment_assigned
Customer assigned to an A/B experiment variant.

```json
{
  "event_name": "experiment_assigned",
  "journey_stage": "acquisition",
  "experiment_id": "exp_checkout_cta_v2",
  "variant_id": "variant_b",
  "properties": {
    "experiment_name": "Checkout CTA Button Copy",
    "variant_name": "Add to Bag",
    "allocation_pct": 50
  }
}
```

### variant_exposed
Experiment variant rendered to the customer.

```json
{
  "event_name": "variant_exposed",
  "journey_stage": "consideration",
  "experiment_id": "exp_checkout_cta_v2",
  "variant_id": "variant_b",
  "properties": {
    "surface": "product_detail_page",
    "component": "add_to_cart_button",
    "variant_label": "Add to Bag"
  }
}
```

### page_load_slow
Client detected a slow page load (threshold: >3 seconds).

```json
{
  "event_name": "page_load_slow",
  "journey_stage": "reliability",
  "properties": {
    "page_url": "/products/sku_1001",
    "load_time_ms": 4850,
    "threshold_ms": 3000,
    "connection_type": "4g",
    "device_type": "mobile"
  }
}
```

### api_error_seen
Client-side API error intercepted by the frontend SDK.

```json
{
  "event_name": "api_error_seen",
  "journey_stage": "reliability",
  "properties": {
    "endpoint": "/api/v1/cart/checkout",
    "http_status": 503,
    "error_code": "SERVICE_UNAVAILABLE",
    "retry_count": 2,
    "device_type": "web"
  }
}
```

## ClickHouse Table Schemas

Full DDL with comments is maintained in `infrastructure/clickhouse/init/` and summarized in `infrastructure/clickhouse/README.md`. `raw_events` is implemented by the Spark ClickHouse sink and JSONL loader. The metric tables are created and have pure Python derivation helpers in `streaming/aggregates.py`; wiring those helpers into a continuous Spark mart writer remains planned.

### raw_events

Grain: one row per source event (`event_id`). Idempotent raw event table loaded by the Spark `foreachBatch` sink or direct JSONL loader. Partitioned by `ingest_date` for efficient time-range queries. 90-day TTL.

Primary sort key: `event_id`; engine: `ReplacingMergeTree(ingested_at)` so replays for the same `event_id` collapse in ClickHouse merges.

### funnel_metrics

Grain: one row per `(window_start, journey_stage, event_name, experiment_id, variant_id)`. Pre-aggregated window counts for dashboards and API funnel responses. The table uses `ReplacingMergeTree(computed_at)` for idempotent rewrites of the same grain.

Primary sort key: `(window_start, journey_stage, event_name, experiment_id, variant_id)`

### session_metrics

Grain: one row per `session_id`, updated when a later batch has fresher session state. Uses `ReplacingMergeTree(updated_at)` so late state updates replace earlier versions.

Primary sort key: `session_id`

Key analytic columns:
- `max_journey_stage`: highest business journey stage reached in this session
- `reached_checkout`, `reached_payment`, `converted`: conversion milestone flags
- `funnel_collapse`: 1 if the session reached checkout but did not convert
- `cart_value_at_abandon`: estimated revenue lost on collapse

### revenue_events

Grain: one row per revenue-relevant event (`payment_attempted`, `payment_succeeded`, `payment_failed`, or `order_completed`). It extracts typed JSON properties such as `cart_value`, `product_id`, `payment_method`, `failure_reason`, `order_id`, plus `leakage` and `resolution` for revenue leakage reporting.

Primary sort key: `(occurred_at, session_id, event_id)`

### experiment_metrics

Grain: one row per `(window_start, experiment_id, variant_id)`. Tracks assignment, exposure, and converted session counts for experiment readouts.

Primary sort key: `(window_start, experiment_id, variant_id)`

### DLQ envelope schema

Implemented testable JSON envelope for records that will be published to the `customer-events-dlq` Redpanda topic in a later live sink step:

| Field              | Type   | Description                                    |
|--------------------|--------|------------------------------------------------|
| `envelope_id`      | string | UUID for the DLQ wrapper                       |
| `event_id`         | string | Original event id or generated fallback UUID   |
| `raw_payload`      | string | Raw rejected message payload                   |
| `error_type`       | string | `parse_error`, `validation_error`, `schema_error`, or `unknown` |
| `error_message`    | string | Human-readable error detail                    |
| `received_at`      | string | ISO-8601 UTC timestamp of ingestion            |
| `dlq_enqueued_at`  | string | ISO-8601 UTC timestamp envelope was created    |

## Schema Version

The `EcommerceEvent` model is versioned via the package `__version__` string. When
breaking schema changes are introduced (field additions are non-breaking; type changes or
removals are breaking), the DLQ topic and ClickHouse table DDL are updated together with
a migration note in CHANGELOG.md.
