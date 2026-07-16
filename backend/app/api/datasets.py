import io
import os

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Dataset, DatasetProfile, Finding, SchemaMapping
from app.schemas.dataset import (
    DatasetOut,
    DatasetUploadResponse,
    ProfileOut,
    RuleConfigUpdate,
    SchemaMappingOut,
    SchemaMappingUpdate,
)
from app.services.pipeline_runner import reset_dataset_for_rerun, run_pipeline_job
from app.services.upload_service import UploadValidationError, new_dataset_id, save_upload, validate_upload

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetOut])
def list_datasets(db: Session = Depends(get_db)):
    return db.query(Dataset).order_by(Dataset.created_at.desc()).all()


@router.post("/upload")
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    db: Session = Depends(get_db),
):
    content = await file.read()
    try:
        ext = validate_upload(file, len(content))
    except UploadValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    dataset_id = new_dataset_id()
    raw_path = save_upload(dataset_id, ext, content)

    dataset = Dataset(
        id=dataset_id,
        filename=os.path.basename(raw_path),
        original_filename=file.filename,
        status="queued",
        raw_file_path=raw_path,
    )
    db.add(dataset)
    db.commit()

    background_tasks.add_task(run_pipeline_job, dataset_id)

    return DatasetUploadResponse(dataset_id=dataset_id, job_id=dataset_id, status="queued").model_dump() | {
        "id": dataset_id,
        "filename": file.filename,
    }


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    dataset_dir = os.path.dirname(dataset.raw_file_path) if dataset.raw_file_path else None
    db.delete(dataset)
    db.commit()

    if dataset_dir and os.path.isdir(dataset_dir):
        import shutil

        shutil.rmtree(dataset_dir, ignore_errors=True)

    return {"status": "deleted", "dataset_id": dataset_id}


@router.get("/{dataset_id}/profile", response_model=ProfileOut)
def get_profile(dataset_id: str, db: Session = Depends(get_db)):
    profile = (
        db.query(DatasetProfile)
        .filter(DatasetProfile.dataset_id == dataset_id)
        .order_by(DatasetProfile.created_at.desc())
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not available yet")
    return ProfileOut(dataset_id=dataset_id, profile=profile.profile_json)


@router.get("/{dataset_id}/schema", response_model=SchemaMappingOut)
def get_schema(dataset_id: str, db: Session = Depends(get_db)):
    mapping = (
        db.query(SchemaMapping)
        .filter(SchemaMapping.dataset_id == dataset_id)
        .order_by(SchemaMapping.created_at.desc())
        .first()
    )
    if mapping is None:
        raise HTTPException(status_code=404, detail="Schema mapping not available yet")
    return SchemaMappingOut(dataset_id=dataset_id, mapping=mapping.mapping_json, confirmed=bool(mapping.confirmed))


@router.patch("/{dataset_id}/schema", response_model=SchemaMappingOut)
def update_schema(dataset_id: str, payload: SchemaMappingUpdate, db: Session = Depends(get_db)):
    mapping = (
        db.query(SchemaMapping)
        .filter(SchemaMapping.dataset_id == dataset_id)
        .order_by(SchemaMapping.created_at.desc())
        .first()
    )
    if mapping is None:
        raise HTTPException(status_code=404, detail="Schema mapping not available yet")
    mapping.mapping_json = payload.mapping
    mapping.confirmed = 1
    db.commit()
    return SchemaMappingOut(dataset_id=dataset_id, mapping=mapping.mapping_json, confirmed=True)


@router.post("/{dataset_id}/rules")
def update_rules(dataset_id: str, payload: RuleConfigUpdate, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if payload.enabled_rules is not None:
        dataset.enabled_rules = payload.enabled_rules
    if payload.custom_rule_configs is not None:
        dataset.custom_rule_configs = payload.custom_rule_configs
    db.commit()
    return {"status": "updated", "enabled_rules": dataset.enabled_rules, "custom_rule_configs": dataset.custom_rule_configs}


@router.post("/{dataset_id}/rerun")
def rerun_dataset(dataset_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Re-submit a job for an existing upload — e.g. after changing rule
    configuration. Used instead of an in-graph feedback loop; see
    project_memory.md 'Manager Question: Workflow Loops'.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not dataset.raw_file_path or not os.path.exists(dataset.raw_file_path):
        raise HTTPException(status_code=400, detail="Original upload file is no longer available")
    if dataset.status == "running":
        raise HTTPException(status_code=409, detail="A pipeline run is already in progress for this dataset")

    reset_dataset_for_rerun(db, dataset)
    background_tasks.add_task(run_pipeline_job, dataset_id)
    return {"dataset_id": dataset_id, "job_id": dataset_id, "status": "queued"}


@router.get("/{dataset_id}/export")
def export_findings(dataset_id: str, format: str = "csv", db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    findings = db.query(Finding).filter(Finding.dataset_id == dataset_id).all()
    rows = [
        {
            "finding_id": f.finding_id,
            "rule_id": f.rule_id,
            "rule_name": f.rule_name,
            "severity": f.severity,
            "risk_score": f.risk_score,
            "status": f.status,
            "audit_explanation": f.audit_explanation,
            "llm_enriched_explanation": f.llm_enriched_explanation,
            "flagged_row_count": len(f.flagged_rows or []),
        }
        for f in findings
    ]
    df = pd.DataFrame(rows)

    if format == "xlsx":
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, sheet_name="findings")
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=findings_{dataset_id}.xlsx"},
        )

    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=findings_{dataset_id}.csv"},
    )
