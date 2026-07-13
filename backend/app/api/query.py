from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Dataset
from app.schemas.dataset import QueryRequest, QueryResponse
from app.services.duckdb_service import QueryValidationError, query_parquet

router = APIRouter(prefix="/datasets", tags=["query"])

MAX_QUERY_ROWS = 500


@router.post("/{dataset_id}/query", response_model=QueryResponse)
def run_query(dataset_id: str, payload: QueryRequest, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not dataset.processed_parquet_path:
        raise HTTPException(status_code=400, detail="Dataset is not ready for querying yet")

    try:
        columns, rows = query_parquet(dataset.processed_parquet_path, payload.sql, limit=MAX_QUERY_ROWS)
    except QueryValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001 - surface DuckDB errors as 400s
        raise HTTPException(status_code=400, detail=f"Query failed: {e}") from e

    return QueryResponse(columns=columns, rows=rows, row_count=len(rows))
