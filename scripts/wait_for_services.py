from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ServiceCheck:
    name: str
    url: str
    expected_text: str | None = None


def _http_get(url: str, timeout: float) -> tuple[int, str]:
    request = Request(url, headers={"User-Agent": "customer-journey-intel-healthcheck"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - local developer health checks only
        body = response.read(4096).decode("utf-8", errors="replace")
        return response.status, body


def check_service(check: ServiceCheck, timeout: float = 2.0) -> tuple[bool, str]:
    try:
        status, body = _http_get(check.url, timeout=timeout)
    except (TimeoutError, URLError, OSError) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if status >= 400:
        return False, f"HTTP {status}"
    if check.expected_text and check.expected_text not in body:
        return False, f"HTTP {status}, missing {check.expected_text!r}"
    return True, f"HTTP {status}"


def wait_for_services(
    checks: list[ServiceCheck],
    timeout_seconds: float,
    interval_seconds: float,
) -> dict[str, str]:
    deadline = time.monotonic() + timeout_seconds
    statuses: dict[str, str] = {}
    while True:
        all_ready = True
        for check in checks:
            ready, detail = check_service(check)
            statuses[check.name] = detail
            all_ready = all_ready and ready
        if all_ready:
            return statuses
        if time.monotonic() >= deadline:
            raise TimeoutError(json.dumps(statuses, sort_keys=True))
        time.sleep(interval_seconds)


def default_checks(args: argparse.Namespace) -> list[ServiceCheck]:
    checks = [
        ServiceCheck("redpanda", args.redpanda_admin_url),
        ServiceCheck("clickhouse", args.clickhouse_ping_url, expected_text="Ok"),
    ]
    if not args.skip_console:
        checks.append(ServiceCheck("redpanda-console", args.redpanda_console_url))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Wait for local Docker Compose services to become healthy."
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="Total seconds to wait.")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between probes.")
    parser.add_argument("--redpanda-admin-url", default="http://localhost:9644/v1/status/ready")
    parser.add_argument("--redpanda-console-url", default="http://localhost:8080/")
    parser.add_argument("--clickhouse-ping-url", default="http://localhost:8123/ping")
    parser.add_argument(
        "--skip-console",
        action="store_true",
        help="Skip Redpanda Console probe if only broker/warehouse readiness is required.",
    )
    args = parser.parse_args()

    try:
        statuses = wait_for_services(default_checks(args), args.timeout, args.interval)
    except TimeoutError as exc:
        print(f"services not ready before timeout: {exc}", file=sys.stderr)
        return 1

    print("services ready: " + json.dumps(statuses, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
