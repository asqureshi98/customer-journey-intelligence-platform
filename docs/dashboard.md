# Portfolio dashboard

Sprint 4 adds a lightweight Streamlit dashboard for reviewers who want a visual walkthrough of the customer journey intelligence story without wiring up a separate BI tool.

## What is implemented

The dashboard is a local app at `src/customer_journey_intel/dashboard/app.py` with five reviewer-facing sections:

1. **Executive overview** — headline sessions, converted sessions visible in the explorer, at-risk revenue, and best experiment conversion rate.
2. **Funnel analysis** — journey-stage/event drop-off table and bar chart.
3. **Revenue leakage** — payment/friction reasons ranked by at-risk revenue.
4. **Experiment performance** — variant conversion-rate comparison for portfolio A/B test storytelling.
5. **Raw/session explorer** — sample raw events plus session-level rows for inspecting individual journeys.

The app is intentionally optional. Core CI imports and tests the data-loading layer without requiring Streamlit.

## Install and run

```bash
# One-time optional dependency install
make setup-dashboard

# Self-contained demo mode; works without Docker or ClickHouse
make dashboard-local
```

Open the Streamlit URL printed in the terminal, usually `http://localhost:8501`.

## Use live local API data

The aggregate panels can point at the FastAPI demo service when metric tables are populated. The current `make load-clickhouse-sample` command loads generated events into `raw_events` for warehouse/raw-event exploration; it does not populate `funnel_metrics`, `session_metrics`, `revenue_events`, or `experiment_metrics` yet. Until the roadmap metric writers/backfill command are implemented, API-backed aggregate panels may be empty and the self-contained dashboard fallback is the best visual demo path.

```bash
make docker-up
make wait-services
make generate-sample
make load-clickhouse-sample
make api-local

# in a second terminal
CJI_API_BASE_URL=http://127.0.0.1:8000 make dashboard-local
```

If the API is unavailable, or if API aggregate tables are empty, the dashboard falls back to honest demo/sample data and shows a warning. The raw explorer reads `data/sample_events.jsonl` when present, so reviewers can still inspect generated event shape without the full stack.

## Screenshot capture instructions

Live screenshots are not committed from this environment. To capture them locally:

1. Run `make setup-dashboard` and `make dashboard-local`.
2. Open the Streamlit URL.
3. Capture these states for a portfolio README or deck:
   - Executive overview tab with all metric cards visible.
   - Funnel analysis tab after `make generate-sample`.
   - Revenue leakage tab showing ranked leakage reasons.
   - Experiment performance tab with conversion-rate bars.
   - Raw/session explorer tab with a selected session.
4. Save screenshots under `docs/assets/dashboard/` if you want to add them later. Keep captions clear about whether data is demo fallback or API-backed local data.

## Current limitations

- This is a portfolio visualization layer, not a production BI deployment.
- Streamlit is optional and excluded from base install/CI dependencies.
- Aggregate charts use the existing local API when `CJI_API_BASE_URL` is set; otherwise they use deterministic demo data.
- Streaming aggregate writers for metric tables remain planned elsewhere in the project roadmap, as noted in the README.
