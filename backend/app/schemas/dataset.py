from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    original_filename: str
    status: str
    current_step: str | None = None
    progress_pct: int
    error: str | None = None
    row_count: int | None = None
    column_count: int | None = None
    enabled_rules: list[str] | None = None
    custom_rule_configs: dict[str, Any] | None = None
    analysis_summary: str | None = None
    created_at: datetime
    updated_at: datetime


class DatasetUploadResponse(BaseModel):
    dataset_id: str
    job_id: str
    status: str


class JobStatusOut(BaseModel):
    job_id: str
    status: str
    current_step: str | None = None
    progress_pct: int
    error: str | None = None


class ProfileOut(BaseModel):
    dataset_id: str
    profile: dict[str, Any]


class SchemaMappingOut(BaseModel):
    dataset_id: str
    mapping: dict[str, Any]
    confirmed: bool


class SchemaMappingUpdate(BaseModel):
    mapping: dict[str, str]


class RuleConfigUpdate(BaseModel):
    enabled_rules: list[str] | None = None
    custom_rule_configs: dict[str, Any] | None = None


class QueryRequest(BaseModel):
    sql: str


class QueryResponse(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int


class NLQueryRequest(BaseModel):
    question: str


class NLQueryResponse(BaseModel):
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
