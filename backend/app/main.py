"""
AEQUITAS — FastAPI application factory.
"""

import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import agents, health, market_data, ml, pricing, signals
from app.config import settings

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    log.info("aequitas_starting", env=settings.app_env, debug=settings.app_debug)
    yield
    log.info("aequitas_shutting_down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AEQUITAS",
        description="Agentic Equity & Quantitative Intelligence Trading Analysis System",
        version="0.6.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        log.error("unhandled_exception", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    app.include_router(health.router, tags=["health"])
    app.include_router(market_data.router, tags=["market-data"])
    app.include_router(pricing.router, tags=["pricing-risk"])
    app.include_router(ml.router, tags=["ml"])
    app.include_router(signals.router, tags=["signals"])
    app.include_router(agents.router, tags=["agents"])

    return app


app = create_app()
