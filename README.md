# Agentic AI Data Analysis Agent

A LangGraph-based agentic analysis engine that ingests structured datasets, cleans them, fits them to a schema, and runs audit-focused procedures. The system utilizes an LLM to generate audit-perspective explanations and allows for SQL querying on cleaned data via DuckDB.

## Key Features

- **Data Ingestion & Cleaning**: Ingests CSV and XLSX files, validates data, and maps it to proper schemas.
- **Audit Rules Engine**: Runs 15 built-in audit rules (e.g., duplicate invoices, threshold breaches, weekend postings) with configurable thresholds.
- **Statistical Analysis**: Performs outlier detection, trend analysis, variance analysis, and distribution analysis (including Benford's Law).
- **LLM-Powered Explanations**: Uses LiteLLM (provider-agnostic, supporting Gemini, OpenAI, Anthropic, etc.) to enrich deterministic audit findings with deeper analysis and insights.
- **SQL Query Interface**: Employs DuckDB for in-memory querying of the cleaned dataset.
- **LangGraph Architecture**: Built as a StateGraph with typed states, tool-calling for the LLM, and composability for future multi-agent integrations.

## Tech Stack

- **Frontend**: Next.js (Dashboard, Uploads, Findings Review, Data Query)
- **Backend API**: FastAPI (REST endpoints, asynchronous job handling)
- **Agent Orchestration**: LangGraph
- **LLM Layer**: LiteLLM
- **In-Memory SQL**: DuckDB
- **Database**: SQLite with Alembic for migrations

## Project Structure

- `frontend/`: The Next.js frontend application.
- `backend/`: The FastAPI backend, LangGraph engine, and LLM integration.
- `artifacts/`: Project artifacts and generated outputs.
- `uploads/`: Local storage for uploaded and processed datasets.
