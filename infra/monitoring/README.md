# Monitoring Stack

1. **Prometheus**
   ```bash
   ./scripts/run-prometheus.sh
   ```
   - Uses `infra/monitoring/docker-compose.yml` to run Prometheus at http://localhost:9090 with scrape targets defined in `prometheus.yml`.

2. **Grafana**
   - Import `infra/monitoring/grafana/dashboard.json` → set datasource UID `PROM` (or edit JSON) and name the dashboard e.g. "NilRAG Orchestration".
   - Alert rules (either in Grafana Alerting or Alertmanager):
     - **Job Failures (Critical):** `sum(increase(jobs_failed_total[5m])) > 0`
     - **Reddit Rate Limit (Warn):** `increase(reddit_rate_limit_hits_total[5m]) > 5`
     - **LLM Budget (Warn):** `increase(llm_tokens_consumed_total[1h]) > (LLM_DAILY_BUDGET_CENTS * 0.8)`
   - Route alerts to PagerDuty using Grafana Alertmanager or the Prometheus Alertmanager integration described below.

3. **Alert Routing**
   - Configure Alertmanager / PagerDuty with the expressions above. Exporters expose metrics on the backend (`:8000/metrics`) and Airflow webserver (`:8080/metrics`).

4. **Runbooks**
   - See `docs/operations/runbooks.md` for the response checklist tied to each alert.
