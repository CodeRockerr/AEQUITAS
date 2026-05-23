"""
AEQUITAS — Health check endpoints.

A health endpoint is the first thing ops teams and load balancers
check. It tells them whether the service is alive and ready to
serve traffic. Railway and Vercel use this to know when your
deploy succeeded.

GET /health        — is the app running at all? (liveness)
GET /health/ready  — is the app ready to serve traffic? (readiness)
"""

import time
from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter()

# Record when the app started (used to calculate uptime)
_start_time = time.time()


class HealthResponse(BaseModel):
    """
    Pydantic model for the health check response.

    Defining a response model does three things:
    1. Validates the data we return (catches bugs)
    2. Documents the response shape in /docs automatically
    3. Gives TypeScript-friendly JSON schema for the frontend
    """

    status: str
    env: str
    version: str
    uptime_seconds: float
    timestamp: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Liveness check — confirms the app process is running.

    Returns 200 OK if the app is alive.
    This is all Railway needs to confirm a successful deploy.
    """
    return HealthResponse(
        status="ok",
        env=settings.app_env,
        version="0.1.0",
        uptime_seconds=round(time.time() - _start_time, 2),
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """
    Readiness check — confirms all dependencies are reachable.

    Returns 200 if the app can serve traffic (DB + Redis up).
    Returns 503 if any dependency is down.

    We'll wire up real DB + Redis checks in Week 2 when we
    add the connection pools. For now it returns 'ok' as a placeholder.
    """
    checks: dict[str, str] = {
        "database": "ok",  # TODO Week 2: real DB ping
        "redis": "ok",  # TODO Week 2: real Redis ping
    }

    all_ok = all(v == "ok" for v in checks.values())

    return ReadinessResponse(
        status="ready" if all_ok else "degraded",
        checks=checks,
    )
