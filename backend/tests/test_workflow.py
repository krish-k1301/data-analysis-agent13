from app.database import SessionLocal
from app.models import Dataset
from app.workflow.graph import analysis_graph
from tests.conftest import SAMPLE_CSV


def _make_dataset_row(dataset_id: str, raw_path: str) -> None:
    db = SessionLocal()
    try:
        db.add(
            Dataset(
                id=dataset_id,
                filename="raw.csv",
                original_filename="raw.csv",
                status="queued",
                raw_file_path=raw_path,
            )
        )
        db.commit()
    finally:
        db.close()


def test_full_pipeline_end_to_end_on_adversarial_sample(db_ready):
    dataset_id = "wf-test-full"
    _make_dataset_row(dataset_id, str(SAMPLE_CSV))

    result = analysis_graph.invoke(
        {
            "dataset_id": dataset_id,
            "job_id": dataset_id,
            "raw_file_path": str(SAMPLE_CSV),
            "enabled_rules": None,
            "custom_rule_configs": {},
        }
    )

    assert result.get("error") is None
    assert result["status"] == "complete"

    findings = result["findings"]
    triggered_rules = {f["rule_id"] for f in findings}
    assert len(triggered_rules) == 15  # every rule fires on the adversarial sample
    assert all(0 <= f["risk_score"] <= 100 for f in findings)
    assert all(f["audit_explanation"] for f in findings)
    assert result["schema_mapping"]
    assert result["profile"]["row_count"] > 0
    assert result["analysis_summary"]


def test_pipeline_fails_gracefully_on_tiny_dataset(db_ready, tmp_path):
    dataset_id = "wf-test-tiny"
    tiny_csv = tmp_path / "tiny.csv"
    tiny_csv.write_text("vendor,amount,date\nAcme,100,2024-01-01\n")
    _make_dataset_row(dataset_id, str(tiny_csv))

    result = analysis_graph.invoke(
        {
            "dataset_id": dataset_id,
            "job_id": dataset_id,
            "raw_file_path": str(tiny_csv),
            "enabled_rules": None,
            "custom_rule_configs": {},
        }
    )

    assert result.get("error") is not None
    assert "fewer than 10 rows" in result["error"]
    # downstream nodes must skip gracefully, not crash
    assert result.get("findings", []) == []


def test_pipeline_fails_gracefully_on_unparseable_file(db_ready, tmp_path):
    dataset_id = "wf-test-bad-file"
    bad_file = tmp_path / "bad.xlsx"
    bad_file.write_bytes(b"not a real xlsx file")
    _make_dataset_row(dataset_id, str(bad_file))

    result = analysis_graph.invoke(
        {
            "dataset_id": dataset_id,
            "job_id": dataset_id,
            "raw_file_path": str(bad_file),
            "enabled_rules": None,
            "custom_rule_configs": {},
        }
    )
    assert result.get("error") is not None


def test_pipeline_respects_enabled_rules_subset(db_ready):
    dataset_id = "wf-test-subset"
    _make_dataset_row(dataset_id, str(SAMPLE_CSV))

    result = analysis_graph.invoke(
        {
            "dataset_id": dataset_id,
            "job_id": dataset_id,
            "raw_file_path": str(SAMPLE_CSV),
            "enabled_rules": ["ROUND_DOLLAR"],
            "custom_rule_configs": {},
        }
    )

    assert result.get("error") is None
    triggered_rules = {f["rule_id"] for f in result["findings"]}
    assert triggered_rules == {"ROUND_DOLLAR"}
