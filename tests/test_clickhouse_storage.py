from customer_journey_intel.storage.clickhouse import build_raw_events_ddl, insert_raw_events_jsonl


class FakeClickHouseClient:
    def __init__(self):
        self.commands = []
        self.inserted = []

    def command(self, sql):
        self.commands.append(sql)

    def insert(self, table, data, column_names):
        self.inserted.append({"table": table, "data": data, "column_names": column_names})


def test_build_raw_events_ddl_defines_clickhouse_journey_table():
    ddl = build_raw_events_ddl(database="customer_journey")

    assert "CREATE TABLE IF NOT EXISTS customer_journey.raw_events" in ddl
    assert "event_id" in ddl
    assert "journey_stage" in ddl
    assert "properties" in ddl
    assert "ENGINE = MergeTree" in ddl


def test_insert_raw_events_jsonl_creates_table_and_inserts_rows():
    client = FakeClickHouseClient()
    lines = [
        '{"event_id":"e1","event_name":"homepage_viewed","occurred_at":"2026-01-01T00:00:00Z",'
        '"received_at":"2026-01-01T00:00:01Z","customer_id":"cust_1","anonymous_id":"anon_1",'
        '"session_id":"sess_1","journey_stage":"discovery","channel":"web",'
        '"experiment_id":null,"variant_id":null,"properties":{"utm_source":"demo"}}'
    ]

    inserted = insert_raw_events_jsonl(client=client, lines=lines, database="customer_journey")

    assert inserted == 1
    assert client.commands
    assert client.inserted[0]["table"] == "customer_journey.raw_events"
    assert client.inserted[0]["column_names"] == [
        "event_id",
        "event_name",
        "occurred_at",
        "received_at",
        "customer_id",
        "anonymous_id",
        "session_id",
        "journey_stage",
        "channel",
        "experiment_id",
        "variant_id",
        "properties",
    ]
    assert client.inserted[0]["data"][0][0] == "e1"
    assert '"utm_source": "demo"' in client.inserted[0]["data"][0][-1]
