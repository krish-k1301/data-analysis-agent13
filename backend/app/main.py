import os
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import datasets, findings, jobs, query, rules
from app.config import settings

BACKEND_DIR = Path(__file__).resolve().parent.parent


def run_migrations() -> None:
    """Apply Alembic migrations up to head on startup. Schema is owned by
    alembic/versions/ (not Base.metadata.create_all), so alembic_version
    stays authoritative and `alembic revision --autogenerate` keeps working.
    """
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    run_migrations()
    yield


app = FastAPI(title="Agentic AI Data Analysis Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(findings.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(rules.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
