-- Initialize database extensions and any seed operations.
-- This runs automatically on first container start.

CREATE EXTENSION IF NOT EXISTS vector;

-- Optional: tune pgvector defaults via ALTER SYSTEM or per-index params at migration time.

