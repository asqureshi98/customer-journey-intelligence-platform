# Documentation index

This documentation set is written for reviewers, recruiters, and engineers who want to understand the customer journey intelligence platform without reverse-engineering the codebase first.

## Reviewer path

1. Read the portfolio narrative in `../README.md`.
2. Open `portfolio_case_study.md` for the business problem, architecture choices, and demo outputs.
3. Review `pipeline_design.md` for the implemented local data path and diagrams.
4. Check `data_quality.md` for contract boundaries, DLQ status, and validation coverage.
5. Use `operational_runbook.md` to run the local stack.
6. Use `roadmap.md` to distinguish implemented, partially implemented, and planned capabilities.

## Diagrams

- [Architecture SVG](assets/architecture.svg)
- [Data flow SVG](assets/data_flow.svg)
- [Analytical model SVG](assets/analytical_model.svg)

## Detailed references

- `data_model.md` — event taxonomy, envelope schema, ClickHouse table grains.
- `demo_script.md` — step-by-step local demo.
- `dashboard.md` — optional Streamlit dashboard walkthrough.
- `runbook.md` — original operations runbook retained for compatibility; `operational_runbook.md` is the reviewer-friendly version.

## Honest scope summary

Implemented: contracts, synthetic journey generation, Redpanda publishing, Spark Kafka parsing/dedupe, raw ClickHouse sink, ClickHouse schemas, aggregate helpers, API endpoints, dashboard demo, data-quality tests, readiness checks, structured logging.

Partially implemented: DLQ end-to-end flow and analytical metric marts. Helpers, table schemas, queries, and tests exist; always-on Spark writers to populate every metric table continuously are still roadmap items.

Planned: production orchestration, object-lake storage, dbt models, monitoring dashboards, real BI deployment, and alert routing.
