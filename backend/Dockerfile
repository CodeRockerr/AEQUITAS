# ═══════════════════════════════════════════════════════════════
#  AEQUITAS Backend — Dockerfile
#  Multi-stage build: keeps the final image lean
# ═══════════════════════════════════════════════════════════════

# ── Stage 1: dependency installer ─────────────────────────────
# We install deps in a separate stage so Docker can cache them.
# If only your code changes (not pyproject.toml), Docker reuses
# the cached dep layer — much faster rebuilds.
FROM python:3.12-slim AS deps

WORKDIR /app

# Install system dependencies needed by some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency spec first (before any app code)
COPY pyproject.toml .

# Install all dependencies
RUN pip install --upgrade pip && \
    pip install -e ".[dev]"

# ── Stage 2: runtime ──────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy system libs needed at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from the deps stage
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Non-root user for security (never run containers as root)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose the port FastAPI runs on
EXPOSE 8000

# Start FastAPI with uvicorn
# --reload = auto-restart when code changes (dev only)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
