# Threat Model (Draft)

| Asset | Threat | Mitigation |
| --- | --- | --- |
| Reddit credentials | API key leak, quota exhaustion | Secrets stored via `scripts/render-secrets.sh`, environment variables, Airflow pools limiting concurrency, alerts on `reddit_rate_limit_hits_total`. |
| LLM spend | Budget blowout via repeated reanalyze/reembed | GraphQL daily budget check (`LLM_DAILY_BUDGET_CENTS`), Prometheus alerts on `llm_tokens_consumed_total`, feature flags to disable mutations. |
| Job data (PII) | Sensitive data entering LLM | DAGs sanitize text (emails + handles) via `sanitize_text`; need automated validation + unit tests. |
| Control Plane auth | Unauthorized job access | GraphQL requires `X-User-ID`/`X-Org-ID` headers validated against `OrganizationMembership`; add JWT/session integration later. |
| DAG failure drift | Jobs stuck in queued state | Reconciler sidecar polls Airflow + metrics alert on `jobs_failed_total`. |

Next steps:
1. Replace viewer stub with authenticated organization scope.
2. Add integration tests ensuring sanitized payload before LLM calls.
3. Implement alert routing (PagerDuty) for the Prometheus rules documented in `infra/monitoring/README.md`.
