# NIL RAG MVP — Development Plan

## 1) Overview & Delivery Strategy
- Purpose: Translate the PRD into a concrete, low-risk build plan that favors maintainability, typed code, and explicit interfaces over ad‑hoc scripts.
- Guiding Principles: small composable modules, typed Python 3.12, clear boundaries, infra-as-code for local dev, deterministic builds, robust tests, and explicit documentation.
- Success: A working MVP that reliably ingests Reddit content daily, curates FAQs, and serves streaming RAG answers via a minimal React UI; all components are easily handoff‑ready.

## 2) Architecture Summary (from PRD, with concrete choices)
- Ingestion Service (Python): Calls Reddit API on a schedule, filters for NIL relevance, curates FAQs, writes to Postgres, and produces embeddings.
- Datastores:
  - PostgreSQL (operational data, plus `pgvector` for local vector search).
  - Vector DB: Start with `pgvector` for MVP simplicity; can swap to managed vector DB later.
- Backend API (Python/FastAPI): REST endpoints for admin/FAQ, and a streaming RAG endpoint.
- Frontend (React + Node/Express): Minimal chat UI with streamed responses, feedback capture.
- Secrets: YAML files outside repo; `.env` contains absolute paths to those files and other config.
- Scheduler: System cron or containerized cron invoking CLI entry point.

## 3) Project Dependencies (explicit and versioned)
System prerequisites
- macOS + Homebrew
- Docker Desktop (compose v2)
- Git
- Python 3.12 (Homebrew: `brew install python@3.12`)
- Node.js 20.x LTS (brew or nvm), npm or pnpm

Python runtime (pin in `requirements.txt` or `pyproject.toml`)
- fastapi ~= 0.115
- uvicorn[standard] ~= 0.30
- pydantic ~= 2.9
- SQLAlchemy ~= 2.0
- alembic ~= 1.13
- psycopg[binary] ~= 3.1  (or `psycopg2-binary`)
- httpx ~= 0.27 (async HTTP client, if not using PRAW)
- praw ~= 7.7 or asyncpraw ~= 7.7 (choose one; see Section 7)
- tenacity ~= 9.0 (retries/backoff)
- python-dotenv ~= 1.0
- pyyaml ~= 6.0
- numpy ~= 1.26
- openai ~= 1.40 (or provider client of choice; abstract via adapter)
- pgvector ~= 0.2 (if using SQLAlchemy helpers)
- langchain-core ~= 0.2 (optional; keep RAG minimal if used at all)

Dev/quality tools
- pytest ~= 8.2, pytest-asyncio ~= 0.23
- coverage ~= 7.6
- mypy ~= 1.10
- ruff ~= 0.6 (lint + import sort)
- black ~= 24.8 (formatter; optional if using ruff format)
- pre-commit ~= 3.7

Node/Frontend
- node 20.x, npm/pnpm
- express ~= 4.x
- react ~= 18.x, react-dom ~= 18.x
- vite or next (choose vite for simplicity)

Database
- PostgreSQL 15+
- `pgvector` extension (for MVP vector search)

LLM/Embedding Providers
- OpenAI (completion + embeddings) by default; support pluggable providers.

## 4) Environment Setup (local)
1. System tools
   - `brew install python@3.12 node@20 postgres` (Postgres optional if using docker only)
   - Install Docker Desktop.
2. Python venv
   - `python3.12 -m venv venv && source venv/bin/activate`
   - `pip install -U pip setuptools wheel`
3. Install backend deps
   - `pip install -r requirements.txt` (to be populated per Section 3)
4. Node deps
   - `npm create vite@latest frontend -- --template react` (or equivalent if scaffolded already)
   - `cd frontend && npm i express` (Node proxy kept separate under `frontend/server`)
5. Databases via docker-compose (recommended)
   - Compose services: `postgres` with `pgvector` enabled.
   - After first start, run `CREATE EXTENSION IF NOT EXISTS vector;` in Postgres.
6. Configuration & secrets
   - `.env` in repo referencing absolute secret paths, e.g.:
     - `SECRETS_DIR=/ABSOLUTE/PATH/TO/secrets`
     - `REDDIT_SECRETS_FILE=/ABSOLUTE/PATH/TO/secrets/reddit.yaml`
     - `LLM_SECRETS_FILE=/ABSOLUTE/PATH/TO/secrets/llm.yaml`
     - `DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/nilrag`
   - `reddit.yaml` contains client_id, client_secret, user_agent, refresh_token.
   - `llm.yaml` contains api_key, model, embedding_model.
7. Migrations
   - Initialize Alembic, generate revision for base schema (Section 6), and apply: `alembic upgrade head`.

## 5) Repository Structure & Conventions
```
.
├─ docs/
├─ infra/
│  ├─ docker-compose.yml
│  └─ db/init.sql                 # create extension vector; seed schemas (optional)
├─ services/
│  ├─ ingestion/
│  │  ├─ __init__.py
│  │  ├─ cli.py                   # entry points for cron/backfill
│  │  ├─ reddit_client.py         # API wrapper
│  │  ├─ filters.py               # NIL relevance, dedupe
│  │  ├─ faq_curator.py           # question extraction/summarization
│  │  ├─ embeddings.py            # embed + upsert to vector store
│  │  └─ models.py                # pydantic models
│  ├─ backend/
│  │  ├─ __init__.py
│  │  ├─ app.py                   # FastAPI app
│  │  ├─ routers/                 # /ingest, /faqs, /chat
│  │  ├─ rag/                     # retrieval + prompt + generation
│  │  └─ schemas.py               # request/response models
│  └─ common/
│     ├─ config.py                # loads .env and YAML secrets
│     ├─ db.py                    # SQLAlchemy session, engine
│     ├─ logging.py               # structured logging
│     └─ types.py                 # shared types
├─ migrations/                    # Alembic
├─ scripts/                       # helper scripts (dev only)
├─ frontend/                      # react app + node proxy
├─ requirements.txt
└─ .env.example
```

Conventions
- Python: ruff + black, mypy strict optional, 90–100% type coverage in core modules.
- Tests: `tests/unit`, `tests/integration`, `tests/e2e`; pytest naming `test_*.py`.
- Commit style: conventional commits (feat/fix/chore/docs/refactor/test).
- ADRs (optional): `docs/adr/` for key decisions (vector DB choice, streaming method, provider abstraction).

## 6) Data Model (initial)
- `raw_posts(id, subreddit, author, title, body, score, url, created_utc, fetched_at, metadata JSONB)`
- `raw_comments(id, post_id, author, body, score, created_utc, fetched_at, metadata JSONB)`
- `faqs(id, question, answer, source_post_id, created_utc, updated_at, tags TEXT[], confidence NUMERIC, metadata JSONB)`
- `ingestion_runs(id, started_at, finished_at, status, error TEXT, counts JSONB)`
- `feedback(id, conversation_id, rating ENUM('useful','not_useful'), comment TEXT, created_at)`
- `documents(id, kind ENUM('post','comment','faq'), ref_id, text, metadata JSONB, created_at)`
- `embeddings(id, document_id, embedding VECTOR(1536), model TEXT, created_at)` (if using pgvector)

Indexes & constraints
- PKs on ids; unique constraints on Reddit IDs to ensure idempotency.
- GIN/BTREE indexes on `subreddit`, `created_utc`, `tags`.
- Vector index (ivfflat) on `embeddings.embedding` with appropriate `lists` parameter.

Retention
- Raw tables retained N weeks (configurable); downstream curated tables (faqs, documents) retained longer.

## 7) Ingestion Service Design
Flow
1. Discover: fetch new threads/comments since `last_success` from `ingestion_runs`.
2. Filter: NIL relevance via keyword/regex + subreddit/topic whitelist; configurable thresholds.
3. Curate: identify QA pairs (question detection heuristics, top comments), summarize with LLM if needed.
4. Persist: upsert raw + curated to Postgres.
5. Embed: chunk documents (300–500 tokens with 50 token overlap), generate embeddings, upsert to vector store.

Implementation Notes
- Choose client: `praw` (simple) or `asyncpraw` (if we want async). MVP can start with `praw` inside a batch job.
- Rate limits: `tenacity` for retry with exponential backoff; respect Reddit API TOS and user agent.
- Idempotency: upserts keyed on Reddit IDs; isolation level `READ COMMITTED`.
- Backfill: CLI flag `--since YYYY-MM-DD` to backfill history on demand.

## 8) RAG Pipeline
- Retriever: top‑k vector search from `embeddings` with metadata filters (subreddit/date/topic).
- Ranker (optional later): simple BM25 re-ranking or LLM re-rank for edge cases.
- Prompting: Include question, curated snippets (with citations), instruction to cite sources and indicate uncertainty.
- Generator: LLM completion with streaming; temperature low for factuality.
- Output: answer, citations (Reddit URLs), confidence, latency.

Chunking & Metadata
- Chunk by sentence/paragraph preserving URLs, authors, timestamps.
- Store subreddit, post_id, comment_id, created_utc, and moderation flags.

## 9) Backend API (FastAPI)
Endpoints (initial)
- `POST /v1/ingest/run` — trigger ingestion (manual). Auth required.
- `GET /v1/faqs` — list FAQs with filters (topic, date, subreddit).
- `POST /v1/chat/stream` — streamed RAG answer; body: `{query: str, filters?: {...}}`.
- `POST /v1/admin/subreddits` (CRUD) — manage monitored subreddits.
- `POST /v1/feedback` — store user feedback for a conversation turn.

Streaming
- Prefer Server‑Sent Events (SSE) or chunked transfer. Return chunks of tokens with periodic partials and final payload with citations.

Security
- Simple API key in header for MVP. Validate against secrets; rotateable.

## 10) Frontend (React + Node/Express)
- Node proxy to backend: forwards `/api/*` to FastAPI; handles SSE and websockets if used.
- Chat UI: input, streamed output view, citation list, feedback buttons.
- Error & empty states: rate limit, provider errors, network loss.
- Telemetry: minimal event logging (query submitted, response streamed, feedback clicked).

## 11) Scheduling & Operations
- Provide `python -m services.ingestion.cli run-daily` entry point.
- Cron example: `0 3 * * * /path/to/venv/bin/python -m services.ingestion.cli run-daily >> /var/log/nilrag/ingest.log 2>&1`
- Job recording in `ingestion_runs`; retries with backoff, alert on persistent failure (email/webhook).

## 12) Security, Compliance, & Secrets
- Secrets live outside repo; `.env` only includes absolute paths and non‑secret config.
- Log redaction for tokens; avoid logging user content at DEBUG in production.
- Respect Reddit TOS; provide user agent string and backoff.
- Consider minimal PII exposure; avoid storing author usernames if not needed for MVP analytics.

## 13) Testing Strategy
- Unit tests: parsing, filters, curation, prompt builders, retriever.
- Integration tests: DB migrations, CRUD, vector search correctness, chat endpoint end‑to‑end with stubbed LLM.
- E2E (local): docker‑compose stack; seeded Reddit fixtures; scripted chat flows.
- Determinism: seed random, record LLM fixtures for regressions.
- Coverage target: ≥80% overall; ≥90% in ingestion and RAG core modules.

## 14) CI/CD (MVP)
- GitHub Actions (or similar):
  - Lint (ruff), format check (black), type check (mypy).
  - Unit + integration tests on push/PR.
  - Build docker images for backend; compose validation.
  - Optional: SAST (Bandit), dependency scanning.

## 15) Milestones, Tasks, Dependencies, Acceptance
Milestone 1 — Ingestion Foundations (1–1.5 weeks)
- Tasks: Base repo structure, config loader, DB schema + migrations, Reddit client, ingestion run (raw posts/comments), idempotent upserts, cron entrypoint, logging.
- Dependencies: Reddit API creds, Docker/Postgres, secrets path.
- Acceptance: Run daily job successfully across ≥5 subreddits; data visible in Postgres; logs + run records present.

Milestone 2 — FAQ Curation & Vector Store (1–1.5 weeks)
- Tasks: NIL filters, question detection, answer summarization, documents table, embeddings pipeline, pgvector index + search.
- Dependencies: LLM provider + embedding model, CPU/memory sizing.
- Acceptance: Top FAQs populated; vector search returns relevant snippets for sample queries.

Milestone 3 — RAG API (1 week)
- Tasks: FastAPI app, retrieval + prompt assembly, streaming endpoint, admin endpoints, auth.
- Dependencies: Vector search operational, LLM provider.
- Acceptance: `POST /v1/chat/stream` streams answers with citations; admin endpoints function.

Milestone 4 — Frontend Agent (0.5–1 week)
- Tasks: React chat UI, Node proxy, SSE handling, feedback capture.
- Dependencies: Backend streaming stable.
- Acceptance: Usable chat with streamed responses and visible citations; feedback stored.

Milestone 5 — Pilot Readiness (0.5 week)
- Tasks: E2E testing, docs, runbooks, light monitoring/alerts, ADRs.
- Dependencies: All earlier milestones.
- Acceptance: Stakeholder sign‑off after demo and review checklist.

## 16) Risks & Mitigations (expanded)
- Reddit API instability/rate limits → Exponential backoff, smaller windows, resilient checkpoints.
- Data quality variance → Human review loop; iterate filters; add lightweight re‑ranking later.
- LLM cost/latency → Cache embeddings; limit retrieved context; batch embeddings.
- Vector DB swap later → Use repository pattern and feature flag for provider.
- Secrets mishandling → Pre‑commit secret scans; strict env loader; .gitignore templates.

## 17) Open Questions & Fallback Defaults
1) Launch subreddits & backfill window → Default: 5 subreddits; backfill 30 days.
2) NIL relevance rules → Start with curated keyword list + subreddit scope; iterate.
3) Vector DB → Default: Postgres + pgvector; revisit for scale.
4) Compliance constraints → Default: retain raw 30 days, curated indefinitely; anonymize authors.
5) LLM/model & budget → Default: OpenAI GPT‑4o (responses) + `text-embedding-3-large`; cap cost via rate limits.
6) Multi‑turn chat → Default: enable short session memory (last 3 turns) stored server‑side.
7) Analytics needs → Default: basic metrics + log-based dashboards.
8) Pilot auth → Default: shared API key; restrict access by network.
9) Content removal → Default: soft‑delete if source removed; nightly cleanup job.
10) Deployment env → Default: local docker‑compose for MVP; cloud later.

## 18) Handoff Deliverables
- Up‑to‑date README, `.env.example`, API reference (OpenAPI), runbooks for ingestion and troubleshooting.
- ADRs for key choices; migration history; test coverage report and CI badges.

## 19) Definition of Done & Quality Gates
- Code: typed, linted, formatted; unit/integration tests added; docs updated.
- Security: no plaintext secrets in repo; dependency scan clean or waivers documented.
- Ops: logs present; failure modes tested; recovery documented.
- Product: acceptance tests pass; demo script validated with stakeholders.

## 20) Appendices
- Example `.env` entries
  - `DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/nilrag`
  - `OPENAI_API_KEY_PATH=/ABS/PATH/secrets/llm.yaml`
  - `REDDIT_SECRETS_FILE=/ABS/PATH/secrets/reddit.yaml`
  - `EMBEDDING_MODEL=text-embedding-3-large`
- Example cron
  - `0 3 * * * /path/to/venv/bin/python -m services.ingestion.cli run-daily`
- Example SQL (pgvector)
  - `CREATE EXTENSION IF NOT EXISTS vector;`
  - `CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);`

