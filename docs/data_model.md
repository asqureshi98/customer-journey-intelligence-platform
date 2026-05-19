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

Full DDL with comments is maintained in
`infrastructure/clickhouse/README.md`. Below is a reference summary.

### raw_events

Append-only full audit trail of every validated event. Partitioned by `ingest_date` for
efficient time-range queries. 90-day TTL.

Primary sort key: `(occurred_at, session_id, event_id)`

### funnel_metrics

Pre-aggregated per-minute window counts used by dashboards. Uses
`AggregatingMergeTree` so partial aggregates from multiple Spark micro-batches can be
merged without double-counting.

Primary sort key: `(window_start, journey_stage, event_name, channel)`

### session_metrics

One row per session, updated when the session times out or completes. Uses
`ReplacingMergeTree(updated_at)` so late state updates replace earlier versions.

Primary sort key: `session_id`

Key analytic columns:
- `max_funnel_stage`: highest stage reached in this session
- `funnel_collapse`: 1 if the session reached checkout but did not convert
- `cart_value_at_abandon`: estimated revenue lost on collapse

### revenue_events

Payment outcomes and revenue leakage records. One row per `payment_attempted` or
`order_completed` event, enriched with leakage flag and experiment metadata.

Primary sort key: `(occurred_at, session_id, event_id)`

### DLQ envelope schema

Published to the `customer-events-dlq` Redpanda topic as JSON:

| Field              | Type   | Description                                    |
|--------------------|--------|------------------------------------------------|
| `original_payload` | string | Raw bytes of the rejected message              |
| `error_type`       | string | Validation error category                      |
| `error_detail`     | string | Pydantic error message                         |
| `received_at`      | string | ISO-8601 UTC timestamp of ingestion            |
| `kafka_partition`  | int    | Source partition for replay targeting          |
| `kafka_offset`     | int    | Source offset for replay targeting             |

## Schema Version

The `EcommerceEvent` model is versioned via the package `__version__` string. When
breaking schema changes are introduced (field additions are non-breaking; type changes or
removals are breaking), the DLQ topic and ClickHouse table DDL are updated together with
a migration note in CHANGELOG.md.
