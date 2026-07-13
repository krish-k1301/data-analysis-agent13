import logging

from app.database import SessionLocal
from app.models import Dataset, Finding
from app.workflow.graph import NODE_PROGRESS, analysis_graph

logger = logging.getLogger(__name__)


def run_pipeline_job(dataset_id: str) -> None:
    """Run the LangGraph analysis pipeline for a dataset. Intended to be
    invoked as a FastAPI BackgroundTask (job_id == dataset_id; one job per
    dataset). Progress is tracked here (not in node return values) so the
    parallel audit_rules/statistics branch never collides on a shared state key.
    """
    db = SessionLocal()
    try:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset is None:
            logger.error("Dataset %s not found for pipeline run", dataset_id)
            return

        dataset.status = "running"
        dataset.progress_pct = 0
        dataset.error = None
        db.commit()

        initial_state = {
            "dataset_id": dataset_id,
            "job_id": dataset_id,
            "raw_file_path": dataset.raw_file_path,
            "enabled_rules": dataset.enabled_rules,
            "custom_rule_configs": dataset.custom_rule_configs or {},
            "status": "running",
        }

        for update in analysis_graph.stream(initial_state, stream_mode="updates"):
            for node_name in update:
                pct = NODE_PROGRESS.get(node_name)
                if pct is None:
                    continue
                dataset.current_step = node_name
                dataset.progress_pct = pct
                db.commit()
    except Exception as e:  # noqa: BLE001 - background task must not raise
        logger.exception("Pipeline run failed for dataset %s", dataset_id)
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset is not None:
            dataset.status = "failed"
            dataset.error = str(e)
            dataset.progress_pct = 100
            db.commit()
    finally:
        db.close()


def reset_dataset_for_rerun(db, dataset: Dataset) -> None:
    """Clear prior findings/status before re-submitting a job (e.g. after the
    user changes rule configuration). Used instead of an in-graph feedback
    loop — see project_memory.md 'Manager Question: Workflow Loops'.
    """
    db.query(Finding).filter(Finding.dataset_id == dataset.id).delete()
    dataset.status = "queued"
    dataset.progress_pct = 0
    dataset.error = None
    db.commit()
