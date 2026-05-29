from customer_journey_intel.api.analytics import ClickHouseAnalyticsRepository


class QueryResult:
    column_names = ["metric"]
    result_rows = [(1,)]


class RecordingClient:
    def __init__(self):
        self.sql: list[str] = []

    def query(self, sql: str):
        self.sql.append(sql)
        return QueryResult()


def repository_sql(method_name: str) -> str:
    client = RecordingClient()
    repository = ClickHouseAnalyticsRepository(client=client)
    getattr(repository, method_name)()
    return client.sql[-1]


def test_funnel_query_targets_funnel_metrics_mart():
    sql = repository_sql("funnel")
    assert ".funnel_metrics" in sql
    assert "conversion_rate" in sql
    assert ".raw_events" not in sql


def test_sessions_query_targets_session_metrics_mart():
    sql = repository_sql("sessions")
    assert ".session_metrics" in sql
    assert "funnel_collapse" in sql
    assert "cart_value_at_abandon" in sql


def test_revenue_leakage_query_targets_revenue_events_and_leakage_flag():
    sql = repository_sql("revenue_leakage")
    assert ".revenue_events" in sql
    assert "WHERE leakage = 1" in sql
    assert "affected_sessions" in sql


def test_experiments_query_targets_experiment_metrics_mart():
    sql = repository_sql("experiments")
    assert ".experiment_metrics" in sql
    assert "assigned_sessions" in sql
    assert "conversion_rate" in sql
