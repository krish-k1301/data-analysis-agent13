import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def _finding_id() -> str:
    return f"FND-{uuid.uuid4()}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Finding(Base):
    __tablename__ = "findings"

    finding_id = Column(String, primary_key=True, default=_finding_id)
    dataset_id = Column(String, ForeignKey("datasets.id"), nullable=False)

    rule_id = Column(String, nullable=False)
    rule_name = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # HIGH|MEDIUM|LOW
    risk_score = Column(Integer, nullable=False, default=0)
    risk_justification = Column(Text, nullable=True)

    flagged_rows = Column(JSON, nullable=False, default=list)
    supporting_metrics = Column(JSON, nullable=False, default=dict)

    audit_explanation = Column(Text, nullable=False, default="")
    llm_enriched_explanation = Column(Text, nullable=True)

    trace = Column(JSON, nullable=False, default=dict)

    status = Column(String, nullable=False, default="PENDING")  # PENDING|CONFIRMED|DISMISSED

    created_at = Column(DateTime(timezone=True), default=_now)

    dataset = relationship("Dataset", back_populates="findings")
    reviews = relationship("ReviewAction", back_populates="finding", cascade="all, delete-orphan")


class ReviewAction(Base):
    __tablename__ = "review_actions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    finding_id = Column(String, ForeignKey("findings.finding_id"), nullable=False)
    action = Column(String, nullable=False)  # CONFIRM|DISMISS|NOTE
    note = Column(Text, nullable=True)
    reviewer = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    finding = relationship("Finding", back_populates="reviews")
