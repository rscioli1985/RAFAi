# AGENTS GUIDE – Airflow + GraphQL Architecture Docs

Welcome! This directory captures every artifact needed to implement and maintain the Airflow-backed GraphQL orchestration effort. Use this guide to stay oriented and avoid duplicating work.

## Directory Map
- `product-requirements/airflow_graphql_integration_prd.md`: Canonical PRD describing architecture, API contracts, operational expectations, and decisions/clarifications. **Read this first** to understand scope and constraints.
- `development-plan/development_plan.md`: Execution blueprint with milestones, workstreams, dependencies, risks, and deliverables. Use it to plan sprints, update status, or derive tickets.
- `development-plan/development-plan-propmt.md`: Original generation prompt; keep it untouched as provenance for future revisions.
- `input.md`: Initial request context for Codex; useful when regenerating docs or confirming intent.
- `../../airflow_dags/`: Source-controlled DAGs plus helpers referenced in the plan (see `airflow_dags/README.md` for usage).
- `schema-versioning.md`: Living log of Alembic migrations + ingestion package expectations.
- `../../infra/secrets/README.md`: Source of truth for secret rendering workflow.
- `../../infra/monitoring/README.md`: Prometheus/Grafana instructions + alerts.
- `../operations/runbooks.md`: Incident response guides.
- `security/threat_model.md` and `qa/soak_load_plan.md`: Supporting docs for §§4.6 and 4.7.

## How To Consume
1. **Align on intent**: Start with the PRD to confirm objectives, architecture, and settled decisions. Capture any new assumptions in the PRD’s Decisions section before coding.
2. **Plan your work**: Derive tasks directly from `development_plan.md`. Update that document if you adjust sequencing, dependencies, or add risks. Never let implementation outpace documented plan changes.
3. **Extend documentation deliberately**:
   - Add new specs (e.g., DAG-specific designs) under a new subfolder and cross-link from AGENTS.md.
   - Preserve prompts (store alongside derived docs) so future agents can regenerate context if needed.
4. **Feedback loop**: When delivering features, annotate `development_plan.md` with completion notes or new blockers, then reflect major architectural changes back into the PRD.
5. **Version control etiquette**: Do not rename or relocate files here without updating AGENTS.md and referencing docs; downstream automation expects these paths.

## Expectations For Future Agents
- Maintain professional, concise technical language consistent with existing docs.
- Document major design or scope changes before implementation so PM/EM stakeholders stay aligned.
- Surface new risks, dependencies, or open questions by updating the Development Plan’s relevant sections.
- When in doubt, add context here for the next person—this directory is the single source of truth for the Airflow orchestration initiative.
