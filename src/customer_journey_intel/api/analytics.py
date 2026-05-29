from __future__ import annotations

from typing import Protocol

from customer_journey_intel.common.settings import Settings


class AnalyticsRepository(Protocol):
    def funnel(self) -> list[dict[str, object]]: ...

    def revenue_leakage(self) -> list[dict[str, object]]: ...

    def sessions(self) -> list[dict[str, object]]: ...

    def experiments(self) -> list[dict[str, object]]: ...


class ClickHouseAnalyticsRepository:
    """Business-ready query repository for portfolio-demo analytics endpoints."""

    def __init__(self, client=None, settings: Settings | None = None) -> None:
        runtime_settings = settings or Settings()
        self.database = runtime_settings.clickhouse_database
        if client is None:
            from clickhouse_connect import get_client

            client = get_client(
                host=runtime_settings.clickhouse_host,
                port=runtime_settings.clickhouse_port,
                database=runtime_settings.clickhouse_database,
                username=runtime_settings.clickhouse_user,
                password=runtime_settings.clickhouse_password,
            )
        self.client = client

    def _query(self, sql: str) -> list[dict[str, object]]:
        result = self.client.query(sql)
        return [dict(zip(result.column_names, row, strict=True)) for row in result.result_rows]

    def funnel(self) -> list[dict[str, object]]:
        return self._query(
            f"""
            WITH totals AS (
                SELECT sum(session_count) AS total_sessions
                FROM {self.database}.funnel_metrics
            )
            SELECT
                journey_stage,
                event_name,
                sum(event_count) AS event_count,
                sum(session_count) AS sessions,
                round(
                    if(totals.total_sessions = 0, 0, sessions / totals.total_sessions), 4
                ) AS conversion_rate
            FROM {self.database}.funnel_metrics
            CROSS JOIN totals
            GROUP BY journey_stage, event_name, totals.total_sessions
            ORDER BY sessions DESC, event_count DESC
            LIMIT 50
            """
        )

    def revenue_leakage(self) -> list[dict[str, object]]:
        return self._query(
            f"""
            SELECT
                coalesce(nullIf(failure_reason, ''), 'unknown') AS failure_reason,
                count() AS failed_payments,
                ifNull(sumIf(cart_value, cart_value IS NOT NULL), 0) AS at_risk_revenue,
                uniq(session_id) AS affected_sessions
            FROM {self.database}.revenue_events
            WHERE leakage = 1
            GROUP BY failure_reason
            ORDER BY at_risk_revenue DESC, failed_payments DESC
            LIMIT 20
            """
        )

    def sessions(self) -> list[dict[str, object]]:
        return self._query(
            f"""
            SELECT
                session_id,
                event_count,
                max_journey_stage AS max_stage,
                first_seen,
                last_seen,
                converted,
                funnel_collapse,
                cart_value_at_abandon
            FROM {self.database}.session_metrics
            ORDER BY funnel_collapse DESC, event_count DESC, last_seen DESC
            LIMIT 50
            """
        )

    def experiments(self) -> list[dict[str, object]]:
        return self._query(
            f"""
            SELECT
                experiment_id,
                variant_id,
                sum(assigned_sessions) AS assigned_sessions,
                sum(exposed_sessions) AS exposed_sessions,
                sum(converted_sessions) AS converted_sessions,
                round(
                    if(assigned_sessions = 0, 0, converted_sessions / assigned_sessions), 4
                ) AS conversion_rate
            FROM {self.database}.experiment_metrics
            GROUP BY experiment_id, variant_id
            ORDER BY conversion_rate DESC, assigned_sessions DESC
            LIMIT 50
            """
        )
