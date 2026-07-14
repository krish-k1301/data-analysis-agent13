# Requirements

## System requirements

- **Python** 3.11+ (developed/tested on 3.13)
- **Node.js** 20+ and npm (developed/tested on Node 22)
- **OS**: Windows, macOS, or Linux
- An LLM API key for at least one supported provider (Gemini, OpenAI, Azure OpenAI, Anthropic) — see `backend/.env.template` for setup. Not required to run the app, only for LLM-powered features (finding explanations, natural-language query); everything else works without a key.

## Backend (Python) dependencies

Installed via `backend/requirements.txt`:

| Package | Purpose |
|---|---|
| fastapi | REST API framework |
| uvicorn[standard] | ASGI server |
| sqlalchemy | ORM / database access |
| alembic | Database migrations |
| pandas | Data cleaning and transformation |
| pyarrow | Parquet read/write for cleaned datasets |
| openpyxl | XLSX file ingestion |
| python-multipart | File upload handling in FastAPI |
| pydantic / pydantic-settings | Request/response validation, settings management |
| scipy | Statistical tests (Benford's Law, z-score/IQR outliers) |
| langgraph | Audit pipeline orchestration (StateGraph) |
| litellm (pinned to 1.91.3) | Provider-agnostic LLM client — pinned because 1.92+ ships a Rust extension with no prebuilt Windows wheel |
| duckdb | In-memory/embedded SQL engine for querying cleaned datasets |
| python-dotenv | Loads `.env` into the process environment |
| pytest / pytest-asyncio / httpx | Test suite |

## Frontend (Node) dependencies

Installed via `frontend/package.json`:

| Package | Purpose |
|---|---|
| next | Application framework (pages, routing, dev/build server) |
| react / react-dom | UI rendering |
| typescript, @types/* | Type checking (dev only) |

No CSS framework — styling is plain CSS (`globals.css`).

## External services

- **LLM provider** (optional, for enrichment/NL-query features): Gemini, OpenAI, Azure OpenAI, Anthropic, or a local Ollama model. Configured entirely through `backend/.env` — see `backend/.env.template`.
- No other external services (database is local SQLite, SQL engine is embedded DuckDB, file storage is local disk).

## Ports

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000` (CORS on the backend is locked to this origin)
