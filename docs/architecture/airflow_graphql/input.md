# Codex Prompt: Generate Product Requirements Document for Airflow-Backed GraphQL Orchestration Layer

## Context

Our application currently has:
- A **React frontend**
- A **FastAPI backend** that exposes a **GraphQL API layer**
- A **Postgres database** for persistence

We are now adding an **asynchronous data orchestration system** for background pipelines such as Reddit scraping, LLM-based analysis, and vector embedding generation.

The orchestration system will be implemented using **Apache Airflow**, which will manage asynchronous and scheduled workflows.  
The FastAPI GraphQL layer will serve as the **control plane** — users will initiate and monitor Airflow jobs via GraphQL mutations and queries, without ever interacting with Airflow directly.

---

## Goal

Generate a comprehensive **Product Requirements Document (PRD)** describing the architecture, requirements, and implementation plan for integrating **Airflow as the asynchronous executor behind the GraphQL API**.

The PRD should be saved in:/docs/architecture/airflow_graphql/airflow_graphql_integration_prd.md

---

## PRD Objectives

The PRD should clearly define:

1. **Architecture Overview**
   - Conceptual diagram (textual description ok) showing the flow between the GraphQL layer, Airflow, workers, and storage.
   - Distinction between the *control plane (GraphQL)* and the *execution plane (Airflow)*.
   - The role of Airflow DAGs in managing scraping, analysis, and embedding tasks.

2. **System Components**
   - **GraphQL Layer (FastAPI + Strawberry/Ariadne)**
     - New mutations (`runScrape`, `reanalyze`, etc.)
     - Job introspection queries (`job(id)`, `jobs(status)`)
   - **Airflow DAGs**
     - DAG responsibilities (scrape → normalize → analyze → embed)
     - Configuration passing via DAG `conf` objects
     - Storage of results and job metadata
   - **Database Layer (Postgres)**
     - Tables for `jobs`, `posts`, `comments`, `analyses`, `embeddings`
     - Airflow → API data flow conventions
   - **Worker & Queue Design**
     - Task retry policies, idempotency, and rate limiting
     - Reddit API key management, backoff, and incremental updates
   - **Vector Indexing**
     - Storage of embeddings (pgvector or external vector DB)
     - Hybrid search (keyword + vector similarity)

3. **Data Flow**
   - Example end-to-end sequence:
     1. GraphQL mutation `runScrape(subreddits, keywords)` invoked
     2. API calls Airflow REST API → creates DAG run with JSON config
     3. Airflow executes scraping and enrichment tasks asynchronously
     4. Results written back to Postgres
     5. GraphQL queries fetch job status and post data

4. **API Schema Additions**
   - Example GraphQL schema types and resolvers
   - Mutations for job submission
   - Queries for job status and results

5. **Operational & Observability Requirements**
   - Logging, job status tracking, and error reporting
   - Syncing Airflow DAG run states with the `jobs` table
   - Metrics for rate limits, task success/failure, and LLM cost usage

6. **Security & Compliance**
   - Rate limiting and sandboxing Reddit access
   - PII stripping before LLM analysis
   - LLM cost control / usage limits per user

7. **Future Extensions**
   - Possible migration from Airflow → Temporal / Dagster
   - Adding subscriptions or real-time job updates via websockets
   - Integrating multi-tenant access control for user-specific workflows

---

## Output Requirements for Codex

- The PRD must be **a single Markdown document**, well-structured with clear section headers, written in a professional tone suitable for product and engineering review.
- It should include:
  - A brief **executive summary**
  - **Architecture diagrams (textual)**
  - **Detailed component breakdown**
  - **Data flow diagrams (in text or Mermaid if supported)**
  - **Open questions** and **next steps**
- Place the generated file in:/docs/architecture/airflow_graphql/airflow_graphql_integration_prd.md


- If the folder doesn’t exist, create it.

---

## Style

Use concise, technical, product-engineering language.  
Use Markdown headers (`##`, `###`), bullet lists, and code blocks where appropriate.  
Avoid verbose prose; favor clarity and specificity.  
Assume the audience includes engineers familiar with GraphQL, FastAPI, and async pipelines, but not Airflow.

---

## Codex Output Command

After reading this prompt, Codex should generate the following file: /docs/architecture/airflow_graphql/airflow_graphql_integration_prd.md

containing the full PRD described above.

---

*End of Prompt*
## Problem Statement
We need to extend the existing FastAPI/GraphQL control plane so it can orchestrate asynchronous Reddit scraping, LLM analysis, and embedding generation workflows that run inside Apache Airflow. The goal is to keep job submission, status tracking, and tenancy logic in the API while delegating long-running data work to Airflow DAGs that write results back to our shared Postgres + pgvector store. Documentation in this directory must capture all decisions that enable that Airflow-backed orchestration layer to launch reliably.

## Stakeholders
- **Product Management (Nil RAG PM):** Owns customer requirements, success metrics, rollout sequencing.
- **Backend/API Team:** Maintains FastAPI GraphQL schema, job persistence, Airflow client integration, and auth controls.
- **Data / ML Engineering:** Authors Airflow DAGs for ingestion, analysis, embeddings, and shared ingestion utilities.
- **DevOps / Platform:** Provides Airflow infrastructure, CI/CD for DAGs, secrets management, and observability plumbing.
- **SRE / Security:** Defines SLIs/SLOs, alerting, incident response, and enforces compliance (PII handling, credential rotation).

## Constraints & Assumptions (from verbal guidance)
1. **Airflow is the mandated orchestrator** for execution-plane work; no alternative workflow engines for this phase.
2. **Single shared Airflow cluster** serves all tenants, so GraphQL must enforce org-level ownership before triggering DAGs.
3. **Postgres + pgvector remain the system of record**; no external vector DB unless scale exceeds current targets.
4. **Reddit + LLM credentials must stay in managed secret stores** (Airflow Connections, Vault/SM); never surface through GraphQL.
5. **Observability is non-negotiable**: every shipped feature needs metrics, logs, and runbooks before being considered complete.
6. **No external SLA yet**, but we must capture runtime metrics to inform future commitments.
7. **Budget controls required**: LLM usage must respect per-org limits; Airflow tasks should short-circuit when budgets are exhausted.
8. **PII handling**: Reddit content must be sanitized before LLM calls; hashed references only when necessary.
9. **Documentation provenance**: Prompts and original requests must stay under `docs/architecture/airflow_graphql/` (per AGENTS guide) so future agents can regenerate context.

_Recorded by Codex based on kickoff conversation and follow-up prompts (2025-10-25)._ 
