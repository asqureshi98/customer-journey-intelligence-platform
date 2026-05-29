from __future__ import annotations

import logging

from fastapi import FastAPI

from customer_journey_intel.api.analytics import AnalyticsRepository, ClickHouseAnalyticsRepository
from customer_journey_intel.api.models import (
    ExperimentMetric,
    FunnelMetric,
    RevenueLeakageMetric,
    SessionMetric,
)
from customer_journey_intel.common.logging import configure_logging
from customer_journey_intel.common.settings import Settings

logger = logging.getLogger(__name__)


def create_app(repository: AnalyticsRepository | None = None) -> FastAPI:
    settings = Settings()
    configure_logging(settings.log_level)
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
        logger.info("health check served", extra={"cji_service": "api"})
        return {"status": "ok", "service": "customer-journey-intel"}

    @app.get("/funnel", response_model=list[FunnelMetric])
    def funnel() -> list[dict[str, object]]:
        return analytics().funnel()

    @app.get("/revenue-leakage", response_model=list[RevenueLeakageMetric])
    def revenue_leakage() -> list[dict[str, object]]:
        return analytics().revenue_leakage()

    @app.get("/sessions", response_model=list[SessionMetric])
    def sessions() -> list[dict[str, object]]:
        return analytics().sessions()

    @app.get("/experiments", response_model=list[ExperimentMetric])
    def experiments() -> list[dict[str, object]]:
        return analytics().experiments()

    return app


app = create_app()
