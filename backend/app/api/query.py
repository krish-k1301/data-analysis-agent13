from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.llm.client import LLMUnavailableError
from app.models import Dataset, DatasetProfile
from app.schemas.dataset import NLQueryRequest, NLQueryResponse, QueryRequest, QueryResponse
from app.services.duckdb_service import QueryValidationError, query_parquet
from app.services.nl_query_service import NLQueryGenerationError, generate_sql_from_question

router = APIRouter(prefix="/datasets", tags=["query"])

MAX_QUERY_ROWS = 500


@router.post("/{dataset_id}/query", response_model=QueryResponse)
def run_query(dataset_id: str, payload: QueryRequest, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset.status != "complete" or not dataset.processed_parquet_path:
        raise HTTPException(status_code=400, detail="Dataset is not ready for querying yet")

    try:
        columns, rows = query_parquet(dataset.processed_parquet_path, payload.sql, limit=MAX_QUERY_ROWS)
    except QueryValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001 - surface DuckDB errors as 400s
        raise HTTPException(status_code=400, detail=f"Query failed: {e}") from e

    return QueryResponse(columns=columns, rows=rows, row_count=len(rows))


@router.post("/{dataset_id}/query/ask", response_model=NLQueryResponse)
def ask_dataset(dataset_id: str, payload: NLQueryRequest, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset.status != "complete" or not dataset.processed_parquet_path:
        raise HTTPException(status_code=400, detail="Dataset is not ready for querying yet")

    profile = (
        db.query(DatasetProfile)
        .filter(DatasetProfile.dataset_id == dataset_id)
        .order_by(DatasetProfile.created_at.desc())
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=400, detail="Dataset profile is not available yet")

    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        sql = generate_sql_from_question(payload.question, profile.profile_json)
    except LLMUnavailableError as e:
        raise HTTPException(status_code=503, detail=f"AI query generation unavailable: {e}") from e
    except NLQueryGenerationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        columns, rows = query_parquet(dataset.processed_parquet_path, sql, limit=MAX_QUERY_ROWS)
    except QueryValidationError as e:
        raise HTTPException(status_code=400, detail=f"Generated query was invalid: {e}") from e
    except Exception as e:  # noqa: BLE001 - surface DuckDB errors as 400s
        raise HTTPException(status_code=400, detail=f"Generated query failed: {sql!r} — {e}") from e

    return NLQueryResponse(sql=sql, columns=columns, rows=rows, row_count=len(rows))
