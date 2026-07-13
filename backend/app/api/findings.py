from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Finding, ReviewAction
from app.schemas.finding import FindingOut, ReviewActionIn, ReviewActionOut

router = APIRouter(tags=["findings"])


@router.get("/findings/dataset/{dataset_id}", response_model=list[FindingOut])
def get_findings_for_dataset(dataset_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Finding)
        .filter(Finding.dataset_id == dataset_id)
        .order_by(Finding.risk_score.desc())
        .all()
    )


@router.get("/datasets/{dataset_id}/findings", response_model=list[FindingOut])
def get_findings_for_dataset_alias(dataset_id: str, db: Session = Depends(get_db)):
    return get_findings_for_dataset(dataset_id, db)


@router.get("/findings/{finding_id}", response_model=FindingOut)
def get_finding(finding_id: str, db: Session = Depends(get_db)):
    finding = db.query(Finding).filter(Finding.finding_id == finding_id).first()
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@router.patch("/findings/{finding_id}/review", response_model=FindingOut)
def review_finding(finding_id: str, payload: ReviewActionIn, db: Session = Depends(get_db)):
    finding = db.query(Finding).filter(Finding.finding_id == finding_id).first()
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")

    action = payload.action.upper()
    if action not in ("CONFIRM", "DISMISS", "NOTE"):
        raise HTTPException(status_code=400, detail="action must be one of CONFIRM, DISMISS, NOTE")

    if action == "CONFIRM":
        finding.status = "CONFIRMED"
    elif action == "DISMISS":
        finding.status = "DISMISSED"

    db.add(
        ReviewAction(
            finding_id=finding_id,
            action=action,
            note=payload.note,
            reviewer=payload.reviewer,
        )
    )
    db.commit()
    db.refresh(finding)
    return finding


@router.get("/findings/{finding_id}/reviews", response_model=list[ReviewActionOut])
def get_finding_reviews(finding_id: str, db: Session = Depends(get_db)):
    return db.query(ReviewAction).filter(ReviewAction.finding_id == finding_id).order_by(ReviewAction.created_at).all()
