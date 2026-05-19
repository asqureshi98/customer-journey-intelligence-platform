from pathlib import Path


def test_makefile_has_stream_api_and_clickhouse_demo_targets():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "stream-local:" in makefile
    assert "api-local:" in makefile
    assert "load-clickhouse-sample:" in makefile
    assert "SPARK_SUBMIT_ARGS" in makefile
