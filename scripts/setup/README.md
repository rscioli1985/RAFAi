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

After those steps you can launch the backend (`./scripts/run-backend.sh`) and frontend as needed. Re-run the seed script any time you want to reset the admin credentials or org metadata.
