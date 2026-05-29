from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FunnelMetric(BaseModel):
    journey_stage: str
    event_name: str
    event_count: int = Field(ge=0)
    sessions: int = Field(ge=0)
    conversion_rate: float = Field(ge=0)


class RevenueLeakageMetric(BaseModel):
    failure_reason: str
    failed_payments: int = Field(ge=0)
    at_risk_revenue: float = Field(ge=0)
    affected_sessions: int = Field(ge=0)


class SessionMetric(BaseModel):
    session_id: str
    event_count: int = Field(ge=0)
    max_stage: str
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    converted: bool = False
    funnel_collapse: bool = False
    cart_value_at_abandon: float | None = Field(default=None, ge=0)


class ExperimentMetric(BaseModel):
    experiment_id: str
    variant_id: str
    assigned_sessions: int = Field(ge=0)
    exposed_sessions: int = Field(ge=0)
    converted_sessions: int = Field(ge=0)
    conversion_rate: float = Field(ge=0)
