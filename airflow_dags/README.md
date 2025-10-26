## Airflow DAGs

This directory contains the orchestration layer defined in the development plan:

- `dags/reddit_ingest.py` – scrapes Reddit posts, filters by keywords, persists them to the shared Postgres tables, and syncs job progress/events back through the GraphQL control plane.
- `dags/analysis_enrich.py` – loads posts from a source job, runs a lightweight summary/sentiment pass, and writes `analyses` rows (now using shared PII sanitization helpers before LLM work).
- `dags/embedding_generate.py` – converts analysis summaries into deterministic embeddings and stores them in `job_embeddings`.

### Running Locally

1. Set `PYTHONPATH` to the repo root so Airflow workers can import `services.*` modules.
2. Ensure `.env` mirrors your database + secrets settings (the DAGs auto-load it via `dotenv`).
3. Copy `infra/airflow/.env.example` → `infra/airflow/.env` and adjust secrets/DB overrides before running `./scripts/run-airflow.sh`.
4. Copy the contents of `airflow_dags/dags` into your Airflow scheduler’s DAG folder _or_ add this directory to `AIRFLOW__CORE__DAGS_FOLDER`.

Each DAG expects `dag_run.conf` to include at least a `job_id` plus the fields described in the PRD (e.g., `subreddits`, `keywords`, `source_job_id`, `post_ids`, etc.). Job status + events are updated through the helper utilities in `airflow_dags/dags/lib/jobs.py`, ensuring GraphQL queries stay in sync.
