from __future__ import annotations

from fastapi import FastAPI

from customer_journey_intel.api.analytics import AnalyticsRepository, ClickHouseAnalyticsRepository


def create_app(repository: AnalyticsRepository | None = None) -> FastAPI:
    app = FastAPI(
        title="Realtime Customer Journey Intelligence API",
        version="0.1.0",
        description="Portfolio API for funnel, session, revenue leakage, and experiment analytics.",
    )
    analytics_repository = repository

    def analytics() -> AnalyticsRepository:
        nonlocal analytics_repository
        if analytics_repository is None:
            analytics_repository = ClickHouseAnalyticsRepository()
        return analytics_repository

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "customer-journey-intel"}

    @app.get("/funnel")
    def funnel() -> list[dict[str, object]]:
        return analytics().funnel()

    @app.get("/revenue-leakage")
    def revenue_leakage() -> list[dict[str, object]]:
        return analytics().revenue_leakage()

    @app.get("/sessions")
    def sessions() -> list[dict[str, object]]:
        return analytics().sessions()

    @app.get("/experiments")
    def experiments() -> list[dict[str, object]]:
        return analytics().experiments()

    return app


app = create_app()
