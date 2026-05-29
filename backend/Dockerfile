# ═══════════════════════════════════════════════════════════════
#  AEQUITAS Backend — Dockerfile
#  Single source of truth: pyproject.toml controls all versions.
#  Never hardcode package versions here.
# ═══════════════════════════════════════════════════════════════

FROM python:3.13-slim

WORKDIR /app

# System dependencies needed to compile C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first
RUN pip install --upgrade pip

# Copy ONLY the dependency spec first.
# Docker caches this layer — if pyproject.toml hasn't changed,
# the entire pip install step is skipped on rebuild. Fast.
COPY pyproject.toml .

# Create minimal package stub so pip editable install works
# before the full source is copied
RUN mkdir -p app && touch app/__init__.py

# Install everything from pyproject.toml — one source of truth
RUN pip install -e ".[dev]"

# Now copy the full application source
# (separate step so code changes don't re-trigger pip install)
COPY . .

# Security: never run as root
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
