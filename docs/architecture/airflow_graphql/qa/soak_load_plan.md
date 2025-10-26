# Soak & Load Test Plan

## Objectives
- Validate job lifecycle under sustained load (soak) and burst traffic (load).
- Capture baseline metrics for job throughput, rate-limit behavior, and LLM costs.

## Scenarios
1. **Soak** – submit 5 `runScrape` jobs/hour for 24h with 3 subreddits each. Expect zero failed jobs, monitor `jobs_failed_total` and `reddit_rate_limit_hits_total`.
2. **Burst load** – submit 20 `reembed` jobs in 5 minutes with varied post counts. Expect Airflow queue to throttle; success criteria is `<5%` failure.
3. **Mixed workload** – combine `runScrape` + `reanalyze` sequentially to ensure cost/budget logic holds.

## Tooling
- Use a simple Python runner (TBD) or k6 script hitting the GraphQL endpoint with service account credentials.
- Enable Prometheus & Grafana to capture metrics; export dashboard snapshots per run.

## Exit Criteria
- No alert fires for >10 minutes once workload stabilizes.
- Mean job completion time < defined SLA (set after first run).
- Document findings + follow-ups in `docs/operations/runbooks.md`.
