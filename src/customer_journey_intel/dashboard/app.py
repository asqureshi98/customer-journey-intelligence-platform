from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any

from customer_journey_intel.dashboard.data import (
    DashboardPayload,
    executive_summary,
    load_dashboard_data,
)


def main() -> None:
    """Run the optional Streamlit app.

    Streamlit stays out of the base dependency set; install with `pip install -e .[dashboard]`.
    """
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised by import smoke tests only
        raise SystemExit(
            "Streamlit is not installed. Run `python -m pip install -e '.[dashboard]'` "
            "or `make setup-dashboard` before `make dashboard-local`."
        ) from exc

    st.set_page_config(
        page_title="Customer Journey Intelligence Demo",
        page_icon="📈",
        layout="wide",
    )
    st.title("Realtime Customer Journey Intelligence")
    st.caption(
        "Portfolio dashboard for funnel health, revenue leakage, experiment performance, "
        "and raw journey exploration."
    )

    api_base_url = os.getenv("CJI_API_BASE_URL")
    payload = load_dashboard_data(api_base_url=api_base_url)
    metadata = payload.get("metadata", {})
    if isinstance(metadata, dict) and metadata.get("warning"):
        st.warning(str(metadata["warning"]))
    elif isinstance(metadata, dict):
        st.info(f"Data source: {metadata.get('source', 'unknown')}")

    overview, funnel, leakage, experiments, explorer = st.tabs(
        [
            "Executive overview",
            "Funnel analysis",
            "Revenue leakage",
            "Experiment performance",
            "Raw/session explorer",
        ]
    )
    with overview:
        render_executive_overview(st, payload)
    with funnel:
        render_funnel_analysis(st, _records(payload, "funnel"))
    with leakage:
        render_revenue_leakage(st, _records(payload, "revenue_leakage"))
    with experiments:
        render_experiment_performance(st, _records(payload, "experiments"))
    with explorer:
        render_session_explorer(st, _records(payload, "sessions"), _records(payload, "raw_events"))


def render_executive_overview(st: Any, payload: DashboardPayload) -> None:
    summary = executive_summary(payload)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Observed sessions", f"{summary['total_sessions']:,}")
    col2.metric("Converted explorer sessions", f"{summary['converted_sessions_in_explorer']:,}")
    col3.metric("Revenue at risk", f"${summary['at_risk_revenue']:,.2f}")
    col4.metric(
        "Best experiment CVR",
        _percentage(float(summary["best_experiment_conversion_rate"])),
    )

    st.subheader("Executive narrative")
    st.write(
        "The dashboard turns the local API/sample data into an executive-ready story: "
        "where customers fall out of the funnel, how much payment friction is worth, "
        "which experiments are moving conversion, and which raw sessions need inspection."
    )
    st.dataframe(_records(payload, "funnel"), use_container_width=True, hide_index=True)


def render_funnel_analysis(st: Any, rows: Sequence[dict[str, Any]]) -> None:
    st.subheader("Journey funnel")
    if not rows:
        st.warning("No funnel rows available yet. Load sample data or start the API.")
        return

    chart_rows = [
        {
            "stage_event": f"{row.get('journey_stage')} · {row.get('event_name')}",
            "sessions": int(row.get("sessions", 0) or 0),
            "conversion_rate": float(row.get("conversion_rate", 0) or 0),
        }
        for row in rows
    ]
    st.bar_chart(chart_rows, x="stage_event", y="sessions")
    st.dataframe(chart_rows, use_container_width=True, hide_index=True)
    st.caption("Conversion rate is measured against the repository/API aggregate session baseline.")


def render_revenue_leakage(st: Any, rows: Sequence[dict[str, Any]]) -> None:
    st.subheader("Revenue leakage")
    if not rows:
        st.warning("No revenue leakage rows available yet.")
        return

    total_at_risk = sum(float(row.get("at_risk_revenue", 0) or 0) for row in rows)
    st.metric("Total at-risk revenue", f"${total_at_risk:,.2f}")
    st.bar_chart(rows, x="failure_reason", y="at_risk_revenue")
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_experiment_performance(st: Any, rows: Sequence[dict[str, Any]]) -> None:
    st.subheader("Experiment performance")
    if not rows:
        st.warning("No experiment rows available yet.")
        return

    display_rows = [
        {
            **row,
            "conversion_rate_percent": round(float(row.get("conversion_rate", 0) or 0) * 100, 2),
        }
        for row in rows
    ]
    st.bar_chart(display_rows, x="variant_id", y="conversion_rate_percent", color="experiment_id")
    st.dataframe(display_rows, use_container_width=True, hide_index=True)


def render_session_explorer(
    st: Any,
    sessions: Sequence[dict[str, Any]],
    raw_events: Sequence[dict[str, Any]],
) -> None:
    st.subheader("Raw/session explorer")
    selected_session = None
    session_ids = [str(row.get("session_id")) for row in sessions if row.get("session_id")]
    if session_ids:
        selected_session = st.selectbox("Inspect session", ["All sessions", *session_ids])
        st.dataframe(sessions, use_container_width=True, hide_index=True)
    else:
        st.warning("No session metrics available yet.")

    visible_events = list(raw_events)
    if selected_session and selected_session != "All sessions":
        visible_events = [row for row in raw_events if row.get("session_id") == selected_session]
    st.dataframe(visible_events, use_container_width=True, hide_index=True)
    st.caption(
        "Raw events come from data/sample_events.jsonl when present; API-backed aggregate "
        "sections use CJI_API_BASE_URL if configured."
    )


def _records(payload: DashboardPayload, key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _percentage(value: float) -> str:
    return f"{value * 100:.1f}%"


if __name__ == "__main__":
    main()
