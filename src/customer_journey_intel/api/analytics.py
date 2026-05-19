from __future__ import annotations

from typing import Protocol

from customer_journey_intel.common.settings import Settings


class AnalyticsRepository(Protocol):
    def funnel(self) -> list[dict[str, object]]: ...

    def revenue_leakage(self) -> list[dict[str, object]]: ...

    def sessions(self) -> list[dict[str, object]]: ...

    def experiments(self) -> list[dict[str, object]]: ...


class ClickHouseAnalyticsRepository:
    """Small query repository for portfolio-demo analytics endpoints."""

    def __init__(self, client=None, settings: Settings | None = None) -> None:
        runtime_settings = settings or Settings()
        self.database = runtime_settings.clickhouse_database
        if client is None:
            from clickhouse_connect import get_client

            client = get_client(
                host=runtime_settings.clickhouse_host,
                port=runtime_settings.clickhouse_port,
                database=runtime_settings.clickhouse_database,
            )
        self.client = client

    def _query(self, sql: str) -> list[dict[str, object]]:
        result = self.client.query(sql)
        return [dict(zip(result.column_names, row, strict=True)) for row in result.result_rows]

    def funnel(self) -> list[dict[str, object]]:
        return self._query(
            f"""
            SELECT
                journey_stage,
                event_name,
                count() AS event_count,
                uniq(session_id) AS sessions
            FROM {self.database}.raw_events
            GROUP BY journey_stage, event_name
            ORDER BY sessions DESC, event_count DESC
            LIMIT 50
            """
        )

    def revenue_leakage(self) -> list[dict[str, object]]:
        return self._query(
            f"""
            SELECT
                JSONExtractString(properties, 'failure_reason') AS failure_reason,
                count() AS failed_payments,
                sumOrNull(JSONExtractFloat(properties, 'cart_value')) AS at_risk_revenue
            FROM {self.database}.raw_events
            WHERE event_name = 'payment_failed'
            GROUP BY failure_reason
            ORDER BY failed_payments DESC
            LIMIT 20
            """
        )

    def sessions(self) -> list[dict[str, object]]:
        return self._query(
            f"""
            SELECT
                session_id,
                count() AS event_count,
                anyLast(journey_stage) AS max_stage,
                min(occurred_at) AS first_seen,
                max(occurred_at) AS last_seen
            FROM {self.database}.raw_events
            GROUP BY session_id
            ORDER BY event_count DESC
            LIMIT 50
            """
        )

    def experiments(self) -> list[dict[str, object]]:
        return self._query(
            f"""
            SELECT
                experiment_id,
                variant_id,
                count() AS events,
                uniq(session_id) AS sessions
            FROM {self.database}.raw_events
            WHERE experiment_id IS NOT NULL
            GROUP BY experiment_id, variant_id
            ORDER BY events DESC
            LIMIT 50
            """
        )
