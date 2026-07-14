# Agentic AI Data Analysis Agent

A LangGraph-based audit analysis engine. It ingests a raw transactions file (CSV or XLSX), cleans it, fits it to a schema, and runs it through 15 audit rules plus a set of statistical checks. Findings get an LLM-generated audit-perspective explanation on top of the deterministic rule output, and the cleaned data can be queried directly with SQL (or with plain English, translated to SQL by an LLM).

## Key features

- Data ingestion and cleaning: ingests CSV and XLSX files, cleans them (whitespace, dates, nulls, dedup, with a change log), and infers column roles (vendor, amount, date, invoice number).
- Audit rules engine: 15 built-in rules (duplicate invoices, threshold breaches, weekend postings, dormant vendors, Benford's Law, and more), each toggleable per dataset with configurable thresholds.
- Statistical analysis: z-score and IQR outlier detection, month-over-month/quarter-over-quarter trend variance, and distribution analysis.
- LLM-powered explanations: LiteLLM (provider-agnostic, supports Gemini, OpenAI, Anthropic, Ollama, and others) enriches each deterministic finding with a richer explanation, falling back to the template explanation if the LLM call fails.
- Natural-language query: ask a question in plain English on the query page and get back a validated, read-only SQL query and its results, run against DuckDB.
- LangGraph pipeline: a 9-node StateGraph (ingest, clean, profile, schema_fit, validate_schema, audit_rules and statistics in parallel, risk_score, explain, persist), designed to be composable into a future multi-agent supervisor.

## LangGraph pipeline

```mermaid
graph TD
    START([start]) --> ingest[ingest]
    ingest --> clean[clean]
    clean --> profile[profile]
    profile --> schema_fit[schema_fit]
    schema_fit --> validate_schema[validate_schema]
    validate_schema --> audit_rules[audit_rules]
    validate_schema --> statistics[statistics]
    audit_rules --> risk_score[risk_score]
    statistics --> risk_score
    risk_score --> explain[explain]
    explain --> persist[persist]
    persist --> END([end])
```

`audit_rules` and `statistics` run in parallel once `validate_schema` passes, then fan into `risk_score`. This matches the node wiring in `backend/app/workflow/graph.py` exactly (see `backend/generate_workflow_image.py` for a PNG rendered straight from the compiled graph object).

## Tech stack

- Frontend: Next.js (dashboard, upload, findings review, data query)
- Backend API: FastAPI (REST endpoints, background job handling with progress polling)
- Agent orchestration: LangGraph
- LLM layer: LiteLLM, with a hosted model (Gemini) for NL-to-SQL and a local Ollama model for per-finding explanations
- In-memory SQL: DuckDB
- Database: SQLite with Alembic for migrations

## Project structure

- `frontend/`: the Next.js frontend application.
- `backend/`: the FastAPI backend, LangGraph engine, audit rules, and LLM integration.
- `artifacts/`: project artifacts and generated outputs.
- `backend/uploads/`: local storage for uploaded and processed datasets.
- `INTERNSHIP_REPORT.md`: full writeup of the project.
