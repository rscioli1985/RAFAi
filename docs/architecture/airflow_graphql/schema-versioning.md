# Schema Versioning & DAG Compatibility

1. **Single Source of Truth** – SQLAlchemy models + Alembic migrations (`migrations/versions/*`) remain authoritative. Every change ships with:
   - Model updates
   - Alembic migration
   - Changelog entry in this document (include migration ID + description)

2. **Versioned ingestion package** – Shared utilities for DAGs live under `services/ingestion/`. DAG containers import these helpers directly from the repo checkout; when we cut a release, tag the repo (`airflow-dags-vX.Y`) and pin the tag in the Airflow image. DAGs should never duplicate persistence logic—extend `services/ingestion/persistence.py` instead.

3. **Release workflow**
   1. Run `alembic upgrade head` locally (already wired in `scripts/setup/db-init.sh`).
   2. Execute `pytest tests/dags/test_imports.py` to ensure DAG modules import with the new schema/helpers.
   3. Build/push the Airflow image (`./scripts/run-airflow.sh` uses the local repo; production should `docker build -f infra/airflow/Dockerfile .`).
   4. Update Airflow deployment to the new tag once migrations have run in the target environment.

4. **Compatibility guarantees**
   - DAGs only read/write through shared helpers (e.g., `persist_posts`, `persist_analysis`), so schema changes funnel through a single surface.
   - Backwards incompatible migrations require a feature flag / DAG toggle; leverage `settings.feature_*` flags to gate GraphQL mutations until all environments are migrated.

5. **Change log**
   - `20251025_0006` – Added orchestration tables (`jobs`, `job_events`, `posts`, `comments`, `analyses`, `job_embeddings`).
   - _Add entries for future migrations here._
