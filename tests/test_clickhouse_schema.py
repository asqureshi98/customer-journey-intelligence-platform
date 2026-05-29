"""Tests for ClickHouse DDL generation for all platform tables."""

from __future__ import annotations

from customer_journey_intel.storage.clickhouse import (
    build_database_ddl,
    build_experiment_metrics_ddl,
    build_funnel_metrics_ddl,
    build_raw_events_ddl,
    build_revenue_events_ddl,
    build_session_metrics_ddl,
    initialize_schema,
)


class FakeCHClient:
    def __init__(self):
        self.commands: list[str] = []

    def command(self, sql: str) -> None:
        self.commands.append(sql)


# ── funnel_metrics ────────────────────────────────────────────────────────────


def test_funnel_metrics_ddl_uses_replacing_merge_tree():
    ddl = build_funnel_metrics_ddl("customer_journey")
    assert "CREATE TABLE IF NOT EXISTS customer_journey.funnel_metrics" in ddl
    assert "ReplacingMergeTree" in ddl


def test_funnel_metrics_ddl_has_window_and_stage_fields():
    ddl = build_funnel_metrics_ddl()
    assert "window_start" in ddl
    assert "window_end" in ddl
    assert "journey_stage" in ddl
    assert "event_name" in ddl
    assert "session_count" in ddl
    assert "event_count" in ddl


def test_funnel_metrics_ddl_has_experiment_fields():
    ddl = build_funnel_metrics_ddl()
    assert "experiment_id" in ddl
    assert "variant_id" in ddl


def test_funnel_metrics_ddl_has_ttl():
    ddl = build_funnel_metrics_ddl()
    assert "TTL" in ddl
    assert "90 DAY" in ddl


# ── session_metrics ───────────────────────────────────────────────────────────


def test_session_metrics_ddl_uses_replacing_merge_tree():
    ddl = build_session_metrics_ddl("customer_journey")
    assert "CREATE TABLE IF NOT EXISTS customer_journey.session_metrics" in ddl
    assert "ReplacingMergeTree" in ddl


def test_session_metrics_ddl_has_session_lifecycle_fields():
    ddl = build_session_metrics_ddl()
    assert "session_id" in ddl
    assert "first_seen" in ddl
    assert "last_seen" in ddl
    assert "event_count" in ddl
    assert "max_journey_stage" in ddl


def test_session_metrics_ddl_has_conversion_flags():
    ddl = build_session_metrics_ddl()
    assert "reached_checkout" in ddl
    assert "reached_payment" in ddl
    assert "converted" in ddl
    assert "funnel_collapse" in ddl
    assert "cart_value_at_abandon" in ddl


def test_session_metrics_order_by_session_id():
    ddl = build_session_metrics_ddl()
    assert "ORDER BY (session_id)" in ddl


# ── revenue_events ────────────────────────────────────────────────────────────


def test_revenue_events_ddl_defines_correct_table():
    ddl = build_revenue_events_ddl("customer_journey")
    assert "CREATE TABLE IF NOT EXISTS customer_journey.revenue_events" in ddl


def test_revenue_events_ddl_has_payment_fields():
    ddl = build_revenue_events_ddl()
    assert "cart_value" in ddl
    assert "product_id" in ddl
    assert "payment_method" in ddl
    assert "failure_reason" in ddl
    assert "leakage" in ddl
    assert "resolution" in ddl
    assert "order_id" in ddl


def test_revenue_events_ddl_has_ttl():
    ddl = build_revenue_events_ddl()
    assert "TTL" in ddl


# ── experiment_metrics ────────────────────────────────────────────────────────


def test_experiment_metrics_ddl_uses_replacing_merge_tree():
    ddl = build_experiment_metrics_ddl("customer_journey")
    assert "CREATE TABLE IF NOT EXISTS customer_journey.experiment_metrics" in ddl
    assert "ReplacingMergeTree" in ddl


def test_experiment_metrics_ddl_has_assignment_and_conversion_fields():
    ddl = build_experiment_metrics_ddl()
    assert "experiment_id" in ddl
    assert "variant_id" in ddl
    assert "assigned_sessions" in ddl
    assert "exposed_sessions" in ddl
    assert "converted_sessions" in ddl


def test_experiment_metrics_ddl_has_window_fields():
    ddl = build_experiment_metrics_ddl()
    assert "window_start" in ddl
    assert "window_end" in ddl


# ── initialize_schema ─────────────────────────────────────────────────────────


def test_initialize_schema_runs_database_and_five_table_ddl_statements():
    client = FakeCHClient()
    ddls = initialize_schema(client, database="customer_journey")
    assert len(ddls) == 6
    assert len(client.commands) == 6


def test_initialize_schema_creates_all_table_names():
    client = FakeCHClient()
    initialize_schema(client, database="cj")
    tables = "\n".join(client.commands)
    assert "CREATE DATABASE IF NOT EXISTS cj" in tables
    assert "cj.raw_events" in tables
    assert "cj.funnel_metrics" in tables
    assert "cj.session_metrics" in tables
    assert "cj.revenue_events" in tables
    assert "cj.experiment_metrics" in tables


def test_raw_events_ddl_is_idempotent_by_event_id():
    ddl = build_raw_events_ddl()
    assert "ENGINE = ReplacingMergeTree(ingested_at)" in ddl
    assert "ORDER BY (event_id)" in ddl
    assert "ingested_at" in ddl


def test_database_ddl_creates_configured_database():
    assert build_database_ddl("cj") == "CREATE DATABASE IF NOT EXISTS cj"
