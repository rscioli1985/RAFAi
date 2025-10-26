Start Database:
./scripts/run-database.sh
  - Script will attempt to launch Docker Desktop automatically on macOS if the daemon is not running.

Seed Default Data:
./scripts/bootstrapping/run-seeds.sh
  - Bootstraps the database (containers + migrations) and creates the admin@goanalog.com user/org.

Run Airflow Orchestrator:
./scripts/run-airflow.sh
  - Builds the Airflow container image, launches the scheduler/webserver (http://localhost:8080), and keeps DAGs in sync with the repo source. Copy `infra/airflow/.env.example` → `infra/airflow/.env` first to set secrets/DB overrides. Pass `--down` to stop and remove the container.

Sync Job Status (Airflow → GraphQL DB):
./scripts/run-reconciler.sh [--interval 60]
  - Polls Airflow DAG runs and updates the `jobs` / `job_events` tables so GraphQL queries stay accurate. Use `--once` for a single pass or run it under a process manager/cron in the background.

Prometheus Metrics:
GET http://localhost:8000/metrics
  - Exposes counters for jobs submitted/completed/failed/canceled; scrape with Prometheus to power the observability dashboards described in the development plan.

Monitor Stack:
./scripts/run-prometheus.sh
  - Starts Prometheus (http://localhost:9090) scraping the backend `/metrics` endpoint (and Airflow if exposed). Use `./scripts/run-prometheus.sh --down` to stop it; edit `infra/monitoring/prometheus.yml` to add more targets.
