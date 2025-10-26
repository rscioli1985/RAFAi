# Airflow-Backed GraphQL Orchestration Development Plan

## 1. Purpose & Scope
Deliver a production-ready orchestration layer where the FastAPI GraphQL control plane manages asynchronous Reddit scraping, LLM analysis, and embedding workflows executed inside Apache Airflow. This plan converts PRD requirements into actionable engineering workstreams with explicit dependencies, milestones, and validation steps.

## 2. Guiding Principles
- Favor explicit contracts between the GraphQL API, Airflow DAGs, and persistence layers to minimize "vibe-coded" coupling.
- Build observability and security controls in parallel with feature work; no task is done until telemetry and alerts exist.
- Keep developer ergonomics high via automation (CI/CD for DAGs, schema packages, typed GraphQL resolvers).

## 3. High-Level Milestones
| Milestone | Target | Entrance Criteria | Exit Criteria |
| --- | --- | --- | --- |
| M0: Foundations Ready | Week 1 | Infra access, repos created | Airflow dev environment provisioned, secrets mgmt defined, baseline schemas in migrations |
| M1: Control Plane MVP | Week 3 | M0 complete | GraphQL mutations/queries + jobs table, mocked DAG trigger path, backend unit tests passing |
| M2: Execution Plane MVP | Week 5 | M1 complete | Airflow DAGs (`reddit_ingest`, `analysis_enrich`, `embedding_generate`) running against dev Postgres, writes verified |
| M3: Observability & Ops | Week 6 | M2 complete | Jobs reconciler, metrics/alerts dashboards, runbooks published |
| M4: Launch Readiness | Week 7 | M3 complete | Security review, load test sign-off, docs for handoff |

## 4. Workstreams & Tasks
### 4.1 Infrastructure & Tooling (supports M0)
1. Provision shared Airflow cluster (dev/stage/prod) with Celery/KubernetesExecutor.
2. Set up separate Airflow metadata Postgres + application Postgres connectivity (read/write roles scoped per DAG).
3. Configure secret management (Airflow Connections + Vault/SM) for Reddit creds, LLM keys, Postgres creds.
4. Create CI/CD pipeline for DAG deployments (linting, unit tests, packaging) and FastAPI schema contract tests. **Status:** `.github/workflows/ci.yml` installs dependencies and runs `pytest` (covering DAG helper/import tests + GraphQL schema checks).
5. Implement Terraform/Ansible modules for Airflow pools, queues, worker autoscaling.
   **Status:** `infra/terraform/airflow/` seeds pools/queues ConfigMaps; extend with provider-specific worker autoscaling.

### 4.2 Database & Schema Evolution (supports M0 → M1)
1. Define SQLAlchemy models + Alembic migrations for `jobs`, `job_events`, `posts`, `comments`, `analyses`, `embeddings` additions.
2. Implement ingestion utility package shared between backend and Airflow tasks for consistent validation/UPSERT logic. **Status:** `services/ingestion/persistence.py` now exposes helpers used by DAGs for posts/analyses.
3. Add pgvector extension enablement + migrations for vector columns and indexes.
4. Document schema versioning strategy for DAGs (package version pinning, release notes). **Status:** `docs/architecture/airflow_graphql/schema-versioning.md` established as the living changelog/process.

### 4.3 GraphQL Control Plane (supports M1)
1. Extend GraphQL schema with Job types, mutations (`runScrape`, `reanalyze`, `reembed`, `cancelJob`) and queries (`job`, `jobs`, `jobResults`).
2. Implement resolvers: validation, job row persistence, Airflow REST client (with retries, auth, circuit breaker).
3. Enforce authZ per organization/user; integrate with existing FastAPI dependency stack.
4. Return structured errors + status transitions; add unit/integration tests using mocked Airflow responses.
5. Add feature flags for new mutations to allow phased rollout. **Status:** `.env` exposes `FEATURE_*` toggles enforced in GraphQL resolvers alongside org-scoped auth filtering + LLM budget checks.
6. **Status:** `jobs` query now supports structured filters + cursor pagination (`JobFilterInput`, `after` cursor) so UI can page through history without bespoke SQL.

### 4.4 Airflow DAG Implementation (supports M2)
> Implementation note: initial DAG scaffolding for `reddit_ingest`, `analysis_enrich`, and `embedding_generate` now lives under `airflow_dags/dags/` along with shared job utilities.
1. Build DAG scaffolding with shared libraries for config parsing, logging, and DB access.
2. `reddit_ingest` DAG tasks: subreddit fetch, comment expansion, normalization, persistence. Include rate-limit pools + exponential backoff.
3. `analysis_enrich` DAG tasks: fetch posts, batch LLM prompts, persist analysis outputs with job relationships.
4. `embedding_generate` DAG tasks: fetch analysis IDs, compute embeddings via pgvector-friendly models, upsert vectors.
   **Status:** DAG now calls `services.ingestion.embeddings.compute_embeddings`, which uses OpenAI when configured and falls back to deterministic vectors, with token metrics recorded.
5. Implement callbacks/webhooks to update `jobs` status + write to `job_events` table.
6. Add automated tests (unit tests for operators, DAG validation tests) + sample data fixtures. **Status:** `tests/dags/test_imports.py` ensures every DAG module imports (skips if Airflow unavailable); wire into CI for full coverage.

### 4.5 Observability & Operations (supports M3)
1. Build reconciliation worker/service to poll Airflow `/dagRuns`, reconcile into `jobs` + `job_events` (handles drift, retries). **Status:** worker lives in `services/backend/orchestration/reconciler.py`, runnable via `./scripts/run-reconciler.sh` and now runs automatically as part of the Airflow docker-compose stack.
2. Emit Prometheus metrics (`jobs_submitted`, `task_failures`, `reddit_rate_limit_hits`, `llm_tokens_consumed`). **Status:** `/metrics` now emits job lifecycle + Reddit rate-limit + LLM token counters; Prometheus docker-compose + config lives in `infra/monitoring/` for local scraping.
3. Configure Grafana dashboards + PagerDuty alerts (backlog, repeated failures, spend caps).
4. Centralize structured logging (Airflow → ELK/CloudWatch) with correlation IDs passed from GraphQL.
5. Document runbooks: DAG failure, API failure, credential rotation, backfill workflow.

### 4.6 Security & Compliance (supports M3 → M4)
1. Implement request throttles and payload guards in GraphQL (max subreddit count, keyword length). **Status:** `runScrape` enforces configurable subreddit/keyword limits via env vars.
2. Ensure Reddit data sanitation prior to LLM tasks; add automated checks for PII stripping. **Status:** DAGs call a shared `sanitize_text` helper to strip emails/user handles before persistence/LLM enrichment; extend with automated validation.
3. Enforce LLM budget checks per organization before enqueuing tasks; add alerts for budget exhaustion. **Status:** resolver checks daily LLM budget (env-configurable) using job cost estimates before triggering DAGs.
4. Conduct threat model + security review; confirm least-privilege roles for Airflow workers.

### 4.7 Launch & QA (supports M4)
1. Run end-to-end soak tests covering job lifecycle, cancellation, idempotency (duplicate submissions, retries).
2. Perform load tests on GraphQL mutations and Airflow DAG throughput under expected concurrency.
3. Validate data correctness (counts, deduplications) via automated comparison jobs.
4. Execute chaos drills (kill worker, drop Reddit access) to verify retry/backoff strategies.
5. Finalize documentation for PM/CS + internal enablement (API docs, dashboards, runbooks).

## 5. Dependencies & Sequencing
- **Infra → App**: Airflow cluster, secrets, and Postgres connectivity must exist before GraphQL resolvers can trigger real DAGs.
- **Schema package**: Alembic migrations and shared ingestion utilities must ship before DAGs to avoid drift.
- **Airflow client**: REST client & auth configuration required ahead of GraphQL mutation rollout.
- **Observability**: Metrics instrumentation depends on DAG task IDs and job schema being finalized.
- **Security**: Reddit credential storage and PII filtering libraries must be in place before LLM tasks execute.
- **Feature parity**: UI/Frontend updates for job monitoring depend on GraphQL query stability (coordinate release schedule).

## 6. Resourcing & Ownership (suggested)
| Workstream | Primary Owner | Supporting |
| Infra/Tooling | DevOps lead | Platform engineer |
| Database & Schema | Backend lead | Airflow engineer |
| GraphQL Control Plane | Backend/API team | QA |
| Airflow DAGs | Data/ML engineer | Backend, DevOps |
| Observability & Ops | SRE | Backend |
| Security & Compliance | Security engineer | Infra, Backend |
| Launch & QA | QA lead | All teams |

## 7. Testing & Validation Strategy
- **Unit tests**: GraphQL resolvers (input validation, error mapping), Airflow operators (idempotency, retry logic), ingestion utilities.
- **Integration tests**: Local Airflow instance triggered via CI to validate DAG wiring against test Postgres.
- **Contract tests**: Ensure GraphQL schema changes are backward-compatible; snapshot `schema.graphql` in repo.
- **Data validation**: Automated QA scripts compare scraped data counts vs. Reddit API responses; verify embeddings count matches analyses.
- **Performance tests**: Simulate concurrent job submissions; measure Airflow queue latency and GraphQL mutation response times.
- **Security tests**: Secrets scanning, ACL verification, penetration testing on GraphQL endpoints.

## 8. Risk Register
| Risk | Impact | Likelihood | Mitigation |
| --- | --- | --- | --- |
| Reddit API rate-limit or auth changes | Pipeline stalls, customer-visible delays | Medium | Implement adaptive backoff, monitor pool usage, keep credentials rotation docs |
| Schema drift between backend and DAGs | Failed writes, data corruption | Medium | Versioned ingestion package, pre-flight migrations, contract tests |
| LLM cost overruns | Budget breach, disabled features | Low-Med | Budget checks, metrics/alerts, kill-switch in GraphQL |
| Airflow cluster saturation | Job backlog, SLA misses | Low | Autoscaling workers, pools, dashboard alerts |
| Security breach of stored Reddit data | Compliance incident | Low | PII scrubbing, least-privilege access, encryption at rest + transit |

## 9. Deliverables Checklist
- [ ] Airflow environments + CI/CD pipeline
- [ ] Alembic migrations + ingestion package published
- [ ] GraphQL schema & resolvers merged with tests
- [ ] DAGs deployed with monitoring + callbacks
- [ ] Reconciliation worker + metrics/alerts live
- [ ] Security controls (rate limits, budget checks, secret storage) validated
- [ ] Runbooks, docs, and handoff materials completed

## 10. Communication Plan
- Weekly sync with PM + engineering leads reviewing milestone burndown.
- Daily async status in #airflow-orchestration channel covering blockers, newly mitigated risks.
- Release readiness review before each environment promotion (dev → stage → prod).

## 11. Next Immediate Actions
1. Confirm infrastructure access + ownership for Airflow cluster (DevOps).
2. Kick off schema/migration work; align versioning strategy between backend and DAG repos.
3. Draft GraphQL schema changes and start mock resolver implementation for UI unblocking.
4. Define metrics/alert requirements with SRE to avoid rework later.
