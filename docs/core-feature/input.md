# Codex Prompt: Generate PRD for Airflow-Backed GraphQL Control Plane with Heavy Backfills

## Context

We have:
- **Frontend:** React (already running)
- **Backend:** FastAPI with a **GraphQL API** (already running)
- **Persistence:** Postgres (and pgvector optional), plus object storage (S3/MinIO) for raw JSON

We are building a system that:
- Ingests Reddit posts/comments (via APIs/tools),
- Runs LLM analysis to summarize sentiment and extract fields,
- Optionally creates embeddings and supports hybrid search,
- Produces topic-focused **reports**,
- **Must support heavy backfills** (days/weeks/months across many subreddits/keywords) with robust retrying, dedupe, lineage, and cost/rate-limit controls.

We will use **Apache Airflow** as the orchestrator. The **GraphQL layer** remains the **control plane** (submit jobs, query job status, fetch results). Airflow is the **execution plane** (plan, parallelize, retry, and monitor).

---

## Goal

Generate a comprehensive **Product Requirements Document (PRD)** that specifies an Airflow-centric architecture optimized for **large, parallel backfills**, while keeping the GraphQL surface stable. The PRD should guide engineering to initial implementation.

**Write the PRD to:**
/docs/architecture/airflow_graphql/airflow_backfills_integration_prd.md

---

## PRD Requirements

### 1) Executive Summary
- One-page summary of the motivation for Airflow (heavy backfills, retries, lineage).
- Control-plane vs execution-plane split (GraphQL ↔ Airflow).
- MVP scope vs later enhancements.

### 2) Architecture Overview
- **Textual diagrams** showing:
  - User → GraphQL mutation (`runBackfill` / `runScrape`) → API calls Airflow REST → DAG runs.
  - DAG graph: `discover_partitions → fetch_raw → normalize → analyze_llm → embed → publish_report`.
  - Storage: S3/MinIO (raw), Postgres (normalized + analysis + job state), pgvector (optional).
- Clear boundaries: GraphQL owns **domain schema**; Airflow owns **work scheduling**.

### 3) Airflow Design for Heavy Backfills
- **Coordinator DAG** to plan and enqueue backfill partitions:
  - Parameterization by `topic`, `subreddits[]`, `keywords[]`, `date_range` (UTC days), and `max_concurrency`.
  - Partitioning strategy: **daily windows per (subreddit × keyword)**; tunable shard sizes for hot subreddits.
  - Dynamic task mapping or task groups for per-partition fan-out.
- **Worker DAG** (or task groups) for each partition:
  - `fetch_raw` with rate-limit aware clients and exponential backoff.
  - `normalize_dedupe` (idempotent UPSERTs keyed by `reddit_id`, plus checksum or `edited` timestamp).
  - `analyze_llm` (batching, token budgets, sampling rules for giant threads).
  - `embed_objects` (optional; delayed if cost/latency dictates).
  - `publish_report_artifacts` (Markdown/HTML) and persist links.
- **Idempotency & Exactly-Once Semantics**
  - Unique constraints on `reddit_id` for posts/comments.
  - Checkpoint tables for watermarks: `ingest_checkpoint(subreddit, keyword, partition_date, high_watermark_created_utc, last_run_id, status)`.
  - Re-runs replace rows atomically (UPSERT) with `model_version` and `analysis_version` columns for provenance.
- **Late-Arrival Handling**
  - Revisit N prior days when running today’s partition.
  - Policy for edits/deletes; soft-delete table with `tombstone_at`.
- **Concurrency & Rate Limits**
  - Airflow pools/queues to isolate Reddit API calls; per-tenant/topic pools optional.
  - Token-bucket manager (shared redis or DB-backed) for the fetcher; DAGs consult before requests.
  - Backpressure rules: cap concurrent partitions; ramp-up on green runs.
- **Retry & Alerting**
  - Task retries with jitter; hard caps; mark partition `partial_success` with skippable next steps.
  - SLA miss alerts; error routing (Slack/email/webhook).
- **Cost/Safety**
  - LLM spend guardrails per run/partition; skip or degrade to heuristic modes when hitting caps.
  - Max items per partition and per-thread truncation rules.

### 4) Data Model & Storage
- **Tables** (Postgres):
  - `job(id, type, params_json, status, created_at, started_at, finished_at, error_text, external_ref_json)` — mirrors Airflow dag_run/task status minimally.
  - `ingest_checkpoint(...)` — per (subreddit, keyword, date) watermark + status.
  - `post(reddit_id UNIQUE, subreddit, title, body, author, created_utc, url, score, edited_utc, raw_ref, inserted_at, updated_at)`
  - `comment(reddit_id UNIQUE, post_reddit_id, body, author, created_utc, edited_utc, raw_ref, inserted_at, updated_at)`
  - `analysis(id, post_reddit_id, run_id, sentiment, summary, fields_json, model, model_version, cost_cents, created_at)`
  - `embedding(id, object_type, object_id, dim, vector, model, model_version, created_at)` (if pgvector)
  - `report(id, run_id, topic, format ENUM('md','html','pdf'), uri, created_at)`
- **Raw Zone**: S3/MinIO bucket layout:
  - `raw/reddit/{subreddit}/{YYYY}/{MM}/{DD}/{keyword}/{shard_id}.jsonl`
- **Provenance**
  - `model_version`, `analysis_version`, and `source_ref` (permalink, fetch timestamp).

### 5) GraphQL Additions (Control Plane)
- **Mutations**
  - `runBackfill(input: { topic, subreddits: [String!], keywords: [String!], dateRange: DateRange!, maxConcurrency: Int, sampleRate: Float, costCapCents: Int }) : Job`
  - `runScrape(input: { subreddits, keywords, since }) : Job`
  - `reanalyze(input: { topic?, dateRange?, filter? }) : Job`
- **Queries**
  - `job(id: ID!): Job { id type status progress startedAt finishedAt error }`
  - `jobs(filter: { type?, status?, from?, to? }): [Job]`
  - `posts(filter: { topic?, subreddits?, keywords?, dateRange? }): [Post]`
  - `reports(filter: { topic?, from?, to? }): [Report]`
- **Status Mapping**
  - Job states mapped from Airflow dag_run/task states; persist snapshots in `job` table for quick reads.
- **Access Control**
  - (If multi-tenant) ensure topics/runs are namespace-scoped; RBAC enforcement in resolvers.

### 6) Backfill Strategy & Controls
- **Partition Planner**
  - Build a list of daily partitions for dateRange × (subreddit × keyword).
  - Skip already-complete partitions unless `force=true`.
  - Optional sampling of heavy partitions (e.g., take top N threads by score).
- **Throttling**
  - Global/max concurrent partitions, per-subreddit concurrency, and per-run quota.
- **Reprocessing**
  - Switchable `analysis_version` or `model_version` triggers reprocessing paths without refetching raw (reuse raw zone).
- **Data Quality**
  - Dedupe policies (hash of title+body; Reddit id uniqueness).
  - NSFW/PII filters pre-LLM.
  - Validation checks: non-empty body/comment thresholds.

### 7) Observability & Ops
- **Metrics**
  - Partitions planned/running/succeeded/failed; records fetched/kept; retry counts; LLM spend; time per stage.
- **Logging**
  - Structured logs with `run_id`, `partition_key`, `task_name`.
- **Lineage**
  - Document lineage in PRD: raw → normalized → analysis → embeddings → report; include dataset versions and retention.
- **Dashboards**
  - Minimal Grafana/Prometheus (or Airflow UI + DB queries) to visualize backfill progress.

### 8) Security & Compliance
- Reddit API key management (Vault/Secrets).
- Respect robots/ToS & rate limits.
- PII stripping and safety filters pre-LLM.
- Data retention and deletion policies for raw and normalized stores.

### 9) Open Questions
- Exact topic taxonomy and report template variants?
- Required SLA for backfills (deadline per N partitions)?
- Multi-tenant needs now or later?
- Which vector store first: pgvector vs external (Qdrant)?
- Cost caps per run and per tenant?

### 10) Acceptance Criteria
- **GraphQL**: mutations/queries above implemented; jobs persisted; status resolvable without live Airflow calls.
- **Airflow**: coordinator + worker DAGs support large date ranges; dynamic partitioning; safe retries; idempotent writes.
- **Storage**: raw zone pathing; normalized schemas created with constraints and indexes.
- **Backfills**: can run a 90-day backfill over ≥10 subreddits × ≥10 keywords with bounded concurrency and no duplicates.
- **Observability**: metrics surfaced; ability to identify slow/failed partitions; LLM spend visible per run.
- **Docs**: PRD includes diagrams (text/Mermaid), example Airflow `conf`, and example GraphQL requests.

---

## Output Requirements for Codex

- Produce **one Markdown PRD** at:/docs/architecture/airflow_graphql/airflow_backfills_integration_prd.md

- Use clear headers, bullet lists, and code blocks (YAML/JSON/SQL/GraphQL) where helpful.
- Include an example Airflow `dag_run` payload (`conf`) and example GraphQL mutation/queries.
- If the folder is missing, create it.

---

## Style

Concise, technical, actionable. Assume engineers know GraphQL/FastAPI; explain Airflow design choices and backfill tactics in detail.

---

*End of Prompt*