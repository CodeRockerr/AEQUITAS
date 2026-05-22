"""
AEQUITAS — FastAPI application factory.

This module creates and configures the FastAPI app instance.
uvicorn imports this as: uvicorn app.main:app
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.v1 import health

# Structured logger — outputs clean JSON in production,
# pretty coloured text in development
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager — runs code on startup and shutdown.

    Everything BEFORE yield runs on startup.
    Everything AFTER yield runs on shutdown.

    This replaces the old @app.on_event("startup") pattern.
    """
    # ── Startup ───────────────────────────────────────────────
    log.info(
        "aequitas_starting",
        env=settings.app_env,
        debug=settings.app_debug,
    )

    # Future: initialise DB connection pool, Redis pool, ML models
    # For now we just log — we'll add real init in Week 2

    yield  # app is running and serving requests here

    # ── Shutdown ──────────────────────────────────────────────
    log.info("aequitas_shutting_down")
    # Future: close DB pools, flush caches, etc.


def create_app() -> FastAPI:
    """
    Application factory — creates and configures the FastAPI instance.

    Using a factory function (rather than a module-level app = FastAPI())
    makes testing easier: each test can create a fresh app instance.
    """
    app = FastAPI(
        title="AEQUITAS",
        description="Agentic Equity & Quantitative Intelligence Trading Analysis System",
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # ── CORS middleware ───────────────────────────────────────
    # CORS (Cross-Origin Resource Sharing) controls which domains
    # can call our API from a browser. Without this, the Next.js
    # frontend on localhost:3000 would be blocked from calling
    # the backend on localhost:8000.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request logging middleware ────────────────────────────
    @app.middleware("http")
    async def log_requests(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Log every request with method, path, status, and duration."""
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

    # ── Global exception handler ──────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Catch any unhandled exception and return a clean JSON error.
        Without this, FastAPI returns an ugly HTML 500 page.
        """
        log.error(
            "unhandled_exception",
            path=request.url.path,
            error=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # ── Routers ───────────────────────────────────────────────
    # Each feature area gets its own router. We include them here.
    # prefix="/api/v1" means all routes are at /api/v1/<route>
    app.include_router(health.router, tags=["health"])

    # Future routers (we'll add these in later steps):
    # app.include_router(signals.router, prefix="/api/v1", tags=["signals"])
    # app.include_router(backtests.router, prefix="/api/v1", tags=["backtests"])
    # app.include_router(agents.router, prefix="/api/v1", tags=["agents"])
    # app.include_router(portfolio.router, prefix="/api/v1", tags=["portfolio"])

    return app


# The app instance uvicorn uses: uvicorn app.main:app
app = create_app()
