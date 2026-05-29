from pathlib import Path


def test_makefile_has_stream_api_and_clickhouse_demo_targets():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "check:" in makefile
    assert "$(RUFF) format --check src tests" in makefile
    assert "$(RUFF) check src tests" in makefile
    assert "$(PYTEST) tests -q" in makefile
    assert "stream-local:" in makefile
    assert "stream-clickhouse:" in makefile
    assert "api-local:" in makefile
    assert "load-clickhouse-sample:" in makefile
    assert "create-topics:" in makefile
    assert "wait-services:" in makefile
    assert "scripts/wait_for_services.py --timeout 90" in makefile
    assert "smoke-local:" in makefile
    assert "e2e-local:" in makefile
    assert "SPARK_SUBMIT_ARGS" in makefile
