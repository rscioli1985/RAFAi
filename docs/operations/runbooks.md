# Runbooks

## DAG Failure (Airflow task failed)
1. Check Prometheus/Grafana for `jobs_failed_total` spikes (dashboard panel 1).
2. Inspect Airflow UI (http://localhost:8080) → DAG → failed run; tail logs.
3. If repeated rate-limit hits, adjust `airflow_pools` Terraform values or reduce mutation concurrency.
4. Re-run job via GraphQL only after root cause is resolved; annotate `job_events` with manual notes if needed.
5. If automated alert fired, acknowledge/resolved via Alertmanager (http://localhost:9093) / PagerDuty.

## Reddit Rate Limit Alert
1. Alert triggers when `reddit_rate_limit_hits_total` > threshold.
2. Verify `airflow_pools` slots for `reddit_api`; reduce subreddits/keywords if necessary.
3. Consider pausing load by toggling `FEATURE_RUN_SCRAPE=false` in `.env` until API quota recovers.
4. Notify product/customer team if ingestion delays expected >2h.

## LLM Budget Exhaustion
1. Alert triggers when tokens consumed exceed 80% of `LLM_DAILY_BUDGET_CENTS` or GraphQL throws “budget exceeded”.
2. Review `llm_tokens_consumed_total` trends; adjust budget env var if intentional, otherwise delay reanalyze/reembed jobs or change model.
3. Communicate timeline for re-enabling LLM jobs in Slack #nilrag-ops.

## Credential / Secret Rotation
1. Run `scripts/render-secrets.sh` to regenerate templates.
2. Update secrets in `$SECRETS_DIR` + `infra/airflow/.env`.
3. Restart backend/Airflow containers so they pick up new credentials.
4. Verify health checks + Prometheus metrics after restart; confirm no unexpected alert noise.
