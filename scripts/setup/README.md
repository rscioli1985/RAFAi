## First-Time Setup

Follow these commands in order the first time you spin up the app locally:

1. **Install Python deps / virtualenv**
   ```bash
   ./scripts/setup/quickstart.sh
   ```
   - Ensures Python 3.12 is available, then creates `.venv` and installs `requirements.txt`.

2. **Initialize the database**
   ```bash
   ./scripts/setup/db-init.sh
   ```
   - Starts the Postgres Docker container (if needed), waits for readiness, and runs Alembic migrations against `postgresql+psycopg://app:app@localhost:5432/nilrag`.

3. **Seed baseline data**
   ```bash
   ./scripts/bootstrapping/run-seeds.sh
   ```
   - Reuses the DB init script above (safe to rerun) and then seeds the default `admin@goanalog.com` user plus the Go Analog organization.

4. **(Optional) Launch Airflow orchestrator container**
   ```bash
   ./scripts/run-airflow.sh
   ```
   - Builds a local Airflow image, mounts the repo (including DAGs), and starts the scheduler/webserver at http://localhost:8080. Copy `infra/airflow/.env.example` → `infra/airflow/.env` to configure secrets/DB connection. Use `./scripts/run-airflow.sh --down` to stop it.

5. **(Optional) Run the job reconciler worker**
   ```bash
   ./scripts/run-reconciler.sh --interval 60
   ```
   - Polls Airflow for DAG run status and syncs the `jobs` table. Use `--once` for manual runs or keep it running alongside Airflow.

6. **(Optional) Start Prometheus monitoring stack**
   ```bash
   ./scripts/run-prometheus.sh
   ```
   - Launches Prometheus at http://localhost:9090 scraping the backend `/metrics` endpoint. Customize `infra/monitoring/prometheus.yml` for additional targets, use `--down` to stop it.

After those steps you can launch the backend (`./scripts/run-backend.sh`) and frontend as needed. Re-run the seed script any time you want to reset the admin credentials or org metadata.
