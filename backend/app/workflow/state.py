from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AnalysisState(TypedDict, total=False):
    # Dataset identity
    dataset_id: str
    job_id: str

    # Pipeline progress (sequential nodes only — audit_rules/statistics run in
    # parallel and intentionally do NOT write these keys, since two parallel
    # branches writing the same un-reduced key raises LangGraph's
    # InvalidUpdateError. Progress for polling is instead tracked by the
    # background task consuming graph.stream(), keyed off node name.)
    status: str
    current_step: str
    progress_pct: int

    # Data artifacts (passed between nodes)
    raw_file_path: str
    processed_parquet_path: str
    dataframe: Any  # pandas.DataFrame — in-memory only, not checkpointed
    profile: dict
    schema_mapping: dict
    cleaning_log: list[dict]
    duckdb_table_name: str

    # Rule configuration
    enabled_rules: list[str]
    custom_rule_configs: dict

    # Results
    findings: list[dict]
    statistics: dict
    analysis_summary: str

    # LLM messages (tool-calling + future agent-to-agent comms)
    messages: Annotated[list, add_messages]

    # Error handling
    error: str | None
