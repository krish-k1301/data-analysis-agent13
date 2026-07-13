from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Dataset
from app.schemas.dataset import JobStatusOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}/status", response_model=JobStatusOut)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    # job_id == dataset_id: one job per dataset (see pipeline_runner.py)
    dataset = db.query(Dataset).filter(Dataset.id == job_id).first()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusOut(
        job_id=job_id,
        status=dataset.status,
        current_step=dataset.current_step,
        progress_pct=dataset.progress_pct,
        error=dataset.error,
    )
