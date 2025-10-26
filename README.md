Start Database:
./scripts/run-database.sh
  - Script will attempt to launch Docker Desktop automatically on macOS if the daemon is not running.

Seed Default Data:
./scripts/bootstrapping/run-seeds.sh
  - Bootstraps the database (containers + migrations) and creates the admin@goanalog.com user/org.
