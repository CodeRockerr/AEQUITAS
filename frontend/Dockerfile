# ═══════════════════════════════════════════════════════════════
#  AEQUITAS Frontend — Dockerfile
# ═══════════════════════════════════════════════════════════════

FROM node:20-alpine AS base

WORKDIR /app

# ── Stage 1: install dependencies ─────────────────────────────
FROM base AS deps

# Copy package files first (layer caching — same trick as backend)
COPY package.json package-lock.json* ./

RUN npm ci

# ── Stage 2: development runtime ──────────────────────────────
FROM base AS dev

# Copy node_modules from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy all source files
COPY . .

EXPOSE 3000

# next dev = hot reload development server
CMD ["npm", "run", "dev"]
