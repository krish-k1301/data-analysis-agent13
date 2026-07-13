from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    finding_id: str
    dataset_id: str
    rule_id: str
    rule_name: str
    severity: str
    risk_score: int
    risk_justification: str | None = None
    flagged_rows: list[dict[str, Any]] = []
    supporting_metrics: dict[str, Any] = {}
    audit_explanation: str
    llm_enriched_explanation: str | None = None
    trace: dict[str, Any] = {}
    status: str
    created_at: datetime


class ReviewActionIn(BaseModel):
    action: str  # CONFIRM|DISMISS|NOTE
    note: str | None = None
    reviewer: str | None = None


class ReviewActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    finding_id: str
    action: str
    note: str | None = None
    reviewer: str | None = None
    created_at: datetime
