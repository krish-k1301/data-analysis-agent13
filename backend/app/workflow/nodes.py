import logging

from app.config import settings
from app.services import cleaning_service, explanation_service, ingestion_service, profiling_service, risk_scoring_service, schema_service, statistics_service
from app.services.audit_rules import registry as rule_registry
from app.services.ingestion_service import IngestionError
from app.workflow.state import AnalysisState

logger = logging.getLogger(__name__)


def _build_config(state: AnalysisState) -> dict:
    config = {
        "materiality_threshold": settings.MATERIALITY_THRESHOLD,
        "MATERIALITY_THRESHOLD": settings.MATERIALITY_THRESHOLD,
        "dormant_vendor_days": settings.DORMANT_VENDOR_DAYS,
        "new_vendor_window_days": settings.NEW_VENDOR_WINDOW_DAYS,
        "new_vendor_high_value": settings.NEW_VENDOR_HIGH_VALUE,
        "vendor_concentration_pct": settings.VENDOR_CONCENTRATION_PCT,
        "benford_p_value": settings.BENFORD_P_VALUE,
        "outlier_zscore_threshold": settings.OUTLIER_ZSCORE_THRESHOLD,
        "split_transaction_window_days": settings.SPLIT_TRANSACTION_WINDOW_DAYS,
    }
    config.update(state.get("custom_rule_configs") or {})
    return config


def ingest_node(state: AnalysisState) -> dict:
    try:
        df = ingestion_service.load_dataframe(state["raw_file_path"])
    except IngestionError as e:
        return {"error": str(e)}
    return {"dataframe": df}


def clean_node(state: AnalysisState) -> dict:
    if state.get("error"):
        return {}
    cleaned, log = cleaning_service.clean_dataframe(state["dataframe"])
    return {"dataframe": cleaned, "cleaning_log": log}


def profile_node(state: AnalysisState) -> dict:
    if state.get("error"):
        return {}
    profile = profiling_service.profile_dataframe(state["dataframe"])
    return {"profile": profile}


def schema_fit_node(state: AnalysisState) -> dict:
    if state.get("error"):
        return {}
    df = state["dataframe"]
    mapping = schema_service.infer_schema_mapping(df)
    df_mapped = schema_service.apply_schema_mapping(df, mapping)
    parquet_path = ingestion_service.write_parquet(df_mapped, state["dataset_id"], settings.UPLOAD_DIR)
    return {
        "dataframe": df_mapped,
        "schema_mapping": mapping,
        "processed_parquet_path": parquet_path,
        "duckdb_table_name": "dataset",
    }


def validate_schema_node(state: AnalysisState) -> dict:
    if state.get("error"):
        return {}
    df = state["dataframe"]
    mapping = state.get("schema_mapping", {})

    errors = []
    if len(df) < 10:
        errors.append("Dataset has fewer than 10 rows after cleaning")
    if len(df.columns) == 0:
        errors.append("Dataset has no columns")
    if not mapping:
        errors.append("No canonical fields (vendor/amount/date/invoice_no) could be mapped")

    if errors:
        return {"error": "; ".join(errors)}
    return {}


def audit_rules_node(state: AnalysisState) -> dict:
    if state.get("error"):
        return {"findings": []}
    df = state["dataframe"]
    config = _build_config(state)
    rules = rule_registry.get_enabled_rules(state.get("enabled_rules"))

    findings: list[dict] = []
    for rule in rules:
        try:
            findings.extend(rule.evaluate(df, config))
        except Exception as e:  # noqa: BLE001 - one bad rule must not crash the run
            logger.warning("Rule %s failed: %s", rule.rule_id, e)
    return {"findings": findings}


def statistics_node(state: AnalysisState) -> dict:
    if state.get("error"):
        return {"statistics": {}}
    config = _build_config(state)
    stats = statistics_service.compute_statistics(state["dataframe"], config)
    return {"statistics": stats}


def risk_score_node(state: AnalysisState) -> dict:
    if state.get("error"):
        return {}
    config = _build_config(state)
    findings = state.get("findings", [])
    statistics = state.get("statistics", {})
    scored = risk_scoring_service.score_findings(findings, statistics, config)
    return {"findings": scored}


def explain_node(state: AnalysisState) -> dict:
    if state.get("error"):
        return {}
    findings = state.get("findings", [])
    df = state["dataframe"]
    context = {"df": df, "parquet_path": state.get("processed_parquet_path")}
    enriched = explanation_service.enrich_findings(findings, context)
    summary = explanation_service.generate_dataset_summary(enriched, state.get("statistics", {}), len(df))
    return {"findings": enriched, "analysis_summary": summary}


def persist_node(state: AnalysisState) -> dict:
    from app.database import SessionLocal
    from app.models import Dataset, DatasetProfile, Finding, SchemaMapping

    db = SessionLocal()
    try:
        dataset = db.query(Dataset).filter(Dataset.id == state["dataset_id"]).first()
        if dataset is None:
            return {"error": f"Dataset {state['dataset_id']} not found during persist"}

        error = state.get("error")
        if error:
            dataset.status = "failed"
            dataset.error = error
            dataset.progress_pct = 100
            db.commit()
            return {"status": "failed"}

        df = state.get("dataframe")
        dataset.row_count = int(len(df)) if df is not None else None
        dataset.column_count = int(len(df.columns)) if df is not None else None
        dataset.processed_parquet_path = state.get("processed_parquet_path")
        dataset.duckdb_table_name = state.get("duckdb_table_name")
        dataset.statistics = state.get("statistics", {})
        dataset.analysis_summary = state.get("analysis_summary", "")
        dataset.status = "complete"
        dataset.error = None
        dataset.progress_pct = 100

        db.add(DatasetProfile(dataset_id=state["dataset_id"], profile_json=state.get("profile", {})))
        db.add(
            SchemaMapping(
                dataset_id=state["dataset_id"],
                mapping_json=state.get("schema_mapping", {}),
                confirmed=0,
            )
        )

        for f in state.get("findings", []):
            db.add(
                Finding(
                    dataset_id=state["dataset_id"],
                    rule_id=f["rule_id"],
                    rule_name=f["rule_name"],
                    severity=f["severity"],
                    risk_score=f.get("risk_score", 0),
                    risk_justification=f.get("risk_justification", ""),
                    flagged_rows=f.get("flagged_rows", []),
                    supporting_metrics=f.get("supporting_metrics", {}),
                    audit_explanation=f.get("audit_explanation", ""),
                    llm_enriched_explanation=f.get("llm_enriched_explanation"),
                    trace=f.get("trace", {}),
                    status="PENDING",
                )
            )

        db.commit()
        return {"status": "complete"}
    except Exception as e:  # noqa: BLE001
        db.rollback()
        return {"error": str(e), "status": "failed"}
    finally:
        db.close()
