-- ═══════════════════════════════════════════════════════════════
--  AEQUITAS — Database initialisation
--  Runs automatically on first Postgres container start.
--  DO NOT put sensitive data here — this is committed to Git.
-- ═══════════════════════════════════════════════════════════════

-- TimescaleDB: turns Postgres into a time-series database.
-- We use this for storing tick data, OHLCV prices, and signals
-- with automatic partitioning by time.
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- pgvector: adds vector similarity search to Postgres.
-- We use this for RAG (storing embeddings of financial documents)
-- instead of a separate vector database like Weaviate.
CREATE EXTENSION IF NOT EXISTS vector;

-- uuid-ossp: lets us generate UUID primary keys in SQL.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
