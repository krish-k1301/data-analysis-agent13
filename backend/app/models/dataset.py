import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String, primary_key=True, default=_uuid)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)

    # Pipeline progress
    status = Column(String, nullable=False, default="queued")  # queued|running|complete|failed
    current_step = Column(String, nullable=True)
    progress_pct = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)

    # Data artifacts
    raw_file_path = Column(String, nullable=True)
    processed_parquet_path = Column(String, nullable=True)
    duckdb_table_name = Column(String, nullable=True)

    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)

    # Rule configuration
    enabled_rules = Column(JSON, nullable=True)  # list[str]
    custom_rule_configs = Column(JSON, nullable=True)  # dict

    # Aggregate output
    statistics = Column(JSON, nullable=True)
    analysis_summary = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    profiles = relationship("DatasetProfile", back_populates="dataset", cascade="all, delete-orphan")
    schema_mappings = relationship("SchemaMapping", back_populates="dataset", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="dataset", cascade="all, delete-orphan")


class DatasetProfile(Base):
    __tablename__ = "dataset_profiles"

    id = Column(String, primary_key=True, default=_uuid)
    dataset_id = Column(String, ForeignKey("datasets.id"), nullable=False)
    profile_json = Column(JSON, nullable=False)  # per-column stats, completeness
    created_at = Column(DateTime(timezone=True), default=_now)

    dataset = relationship("Dataset", back_populates="profiles")


class SchemaMapping(Base):
    __tablename__ = "schema_mappings"

    id = Column(String, primary_key=True, default=_uuid)
    dataset_id = Column(String, ForeignKey("datasets.id"), nullable=False)
    mapping_json = Column(JSON, nullable=False)  # {role: source_column}
    confirmed = Column(Integer, nullable=False, default=0)  # 0/1 boolean (sqlite-friendly)
    created_at = Column(DateTime(timezone=True), default=_now)

    dataset = relationship("Dataset", back_populates="schema_mappings")
