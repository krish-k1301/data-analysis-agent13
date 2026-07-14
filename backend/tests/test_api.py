from tests.conftest import SAMPLE_CSV


def _small_csv_bytes() -> bytes:
    """15 rows spanning 2024-01-02..01-16 (includes Sat 01-06 / Sun 01-07),
    unique invoice/vendor/amount per row so only WEEKEND_POSTING is
    guaranteed to fire under default rule config — deterministic, not
    dependent on incidental data.
    """
    rows = ["invoice_no,vendor,amount,date"]
    for i in range(15):
        rows.append(f"INV-{1000 + i},Vendor{i % 3},{100 + i}.00,2024-01-{2 + i:02d}")
    return ("\n".join(rows) + "\n").encode()


def test_upload_missing_file_returns_422(client):
    resp = client.post("/api/datasets/upload")
    assert resp.status_code == 422


def test_upload_rejects_bad_extension(client):
    resp = client.post(
        "/api/datasets/upload",
        files={"file": ("data.txt", b"not a csv", "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_and_status_and_findings_roundtrip(client):
    resp = client.post(
        "/api/datasets/upload",
        files={"file": ("small.csv", _small_csv_bytes(), "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    dataset_id = body["dataset_id"]
    assert body["job_id"] == dataset_id
    assert body["id"] == dataset_id

    # TestClient runs BackgroundTasks synchronously before returning the
    # response, so the pipeline has already finished by this point.
    status_resp = client.get(f"/api/jobs/{dataset_id}/status")
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["status"] == "complete", status_body
    assert status_body["progress_pct"] == 100

    findings_resp = client.get(f"/api/findings/dataset/{dataset_id}")
    assert findings_resp.status_code == 200
    findings = findings_resp.json()
    assert any(f["rule_id"] == "WEEKEND_POSTING" for f in findings)

    dataset_resp = client.get(f"/api/datasets/{dataset_id}")
    assert dataset_resp.status_code == 200
    dataset_body = dataset_resp.json()
    assert dataset_body["row_count"] == 15
    assert dataset_body["analysis_summary"]

    # aliased route from implementation_plan.md must return the same data
    alias_resp = client.get(f"/api/datasets/{dataset_id}/findings")
    assert alias_resp.status_code == 200
    assert len(alias_resp.json()) == len(findings)


def test_list_all_findings_across_datasets(client):
    resp = client.post(
        "/api/datasets/upload",
        files={"file": ("small.csv", _small_csv_bytes(), "text/csv")},
    )
    dataset_id = resp.json()["dataset_id"]

    all_resp = client.get("/api/findings")
    assert all_resp.status_code == 200
    all_findings = all_resp.json()
    assert any(f["dataset_id"] == dataset_id for f in all_findings)

    scoped = client.get(f"/api/findings/dataset/{dataset_id}").json()
    assert len(all_findings) >= len(scoped)


def test_get_unknown_dataset_returns_404(client):
    resp = client.get("/api/datasets/does-not-exist")
    assert resp.status_code == 404


def test_get_unknown_job_returns_404(client):
    resp = client.get("/api/jobs/does-not-exist/status")
    assert resp.status_code == 404


def test_findings_for_unknown_dataset_returns_empty_list(client):
    resp = client.get("/api/findings/dataset/does-not-exist")
    assert resp.status_code == 200
    assert resp.json() == []


def test_review_unknown_finding_returns_404(client):
    resp = client.patch("/api/findings/does-not-exist/review", json={"action": "confirm"})
    assert resp.status_code == 404


def test_review_confirm_and_invalid_action(client):
    upload = client.post("/api/datasets/upload", files={"file": ("small.csv", _small_csv_bytes(), "text/csv")})
    dataset_id = upload.json()["dataset_id"]
    findings = client.get(f"/api/findings/dataset/{dataset_id}").json()
    assert findings, "expected WEEKEND_POSTING to have fired"
    finding_id = findings[0]["finding_id"]

    bad_resp = client.patch(f"/api/findings/{finding_id}/review", json={"action": "not-a-real-action"})
    assert bad_resp.status_code == 400

    ok_resp = client.patch(
        f"/api/findings/{finding_id}/review",
        json={"action": "confirm", "note": "verified", "reviewer": "test-auditor"},
    )
    assert ok_resp.status_code == 200
    assert ok_resp.json()["status"] == "CONFIRMED"

    reviews_resp = client.get(f"/api/findings/{finding_id}/reviews")
    assert reviews_resp.status_code == 200
    assert len(reviews_resp.json()) == 1


def test_query_rejects_injection_via_api(client):
    upload = client.post("/api/datasets/upload", files={"file": ("small.csv", _small_csv_bytes(), "text/csv")})
    dataset_id = upload.json()["dataset_id"]
    resp = client.post(
        f"/api/datasets/{dataset_id}/query",
        json={"sql": "SELECT * FROM dataset; DROP TABLE dataset;"},
    )
    assert resp.status_code == 400


def test_query_valid_sql_via_api(client):
    upload = client.post("/api/datasets/upload", files={"file": ("small.csv", _small_csv_bytes(), "text/csv")})
    dataset_id = upload.json()["dataset_id"]
    resp = client.post(f"/api/datasets/{dataset_id}/query", json={"sql": "SELECT COUNT(*) as n FROM dataset"})
    assert resp.status_code == 200
    assert resp.json()["rows"][0]["n"] == 15


def test_query_against_unready_dataset_returns_400(client):
    # A dataset row that exists but never finished processing has no parquet yet.
    from app.database import SessionLocal
    from app.models import Dataset

    db = SessionLocal()
    try:
        db.add(Dataset(id="not-ready-ds", filename="x.csv", original_filename="x.csv", status="queued"))
        db.commit()
    finally:
        db.close()

    resp = client.post("/api/datasets/not-ready-ds/query", json={"sql": "SELECT 1"})
    assert resp.status_code == 400


def test_rules_list(client):
    resp = client.get("/api/rules")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 15
    assert {"rule_id", "rule_name", "severity", "category", "required_columns"} <= body[0].keys()


def test_rule_config_update_and_rerun(client):
    upload = client.post("/api/datasets/upload", files={"file": ("small.csv", _small_csv_bytes(), "text/csv")})
    dataset_id = upload.json()["dataset_id"]

    resp = client.post(
        f"/api/datasets/{dataset_id}/rules",
        json={"enabled_rules": ["ROUND_DOLLAR"], "custom_rule_configs": {"round_dollar_min_amount": 50}},
    )
    assert resp.status_code == 200
    assert resp.json()["enabled_rules"] == ["ROUND_DOLLAR"]

    rerun_resp = client.post(f"/api/datasets/{dataset_id}/rerun")
    assert rerun_resp.status_code == 200
    assert rerun_resp.json()["status"] == "queued"

    findings = client.get(f"/api/findings/dataset/{dataset_id}").json()
    assert findings  # all 15 rows are round-dollar amounts > $50
    assert all(f["rule_id"] == "ROUND_DOLLAR" for f in findings)


def test_rerun_unknown_dataset_returns_404(client):
    resp = client.post("/api/datasets/does-not-exist/rerun")
    assert resp.status_code == 404


def test_export_csv_and_xlsx(client):
    upload = client.post("/api/datasets/upload", files={"file": ("small.csv", _small_csv_bytes(), "text/csv")})
    dataset_id = upload.json()["dataset_id"]

    csv_resp = client.get(f"/api/datasets/{dataset_id}/export?format=csv")
    assert csv_resp.status_code == 200
    assert "finding_id" in csv_resp.text

    xlsx_resp = client.get(f"/api/datasets/{dataset_id}/export?format=xlsx")
    assert xlsx_resp.status_code == 200
    assert xlsx_resp.headers["content-type"].startswith("application/vnd.openxmlformats")


def test_delete_cascades_findings_and_files(client):
    import os

    upload = client.post("/api/datasets/upload", files={"file": ("small.csv", _small_csv_bytes(), "text/csv")})
    dataset_id = upload.json()["dataset_id"]
    dataset_before = client.get(f"/api/datasets/{dataset_id}").json()

    del_resp = client.delete(f"/api/datasets/{dataset_id}")
    assert del_resp.status_code == 200

    assert client.get(f"/api/datasets/{dataset_id}").status_code == 404
    assert client.get(f"/api/findings/dataset/{dataset_id}").json() == []


def test_delete_unknown_dataset_returns_404(client):
    resp = client.delete("/api/datasets/does-not-exist")
    assert resp.status_code == 404


def test_list_datasets_includes_uploaded(client):
    upload = client.post("/api/datasets/upload", files={"file": ("small.csv", _small_csv_bytes(), "text/csv")})
    dataset_id = upload.json()["dataset_id"]
    resp = client.get("/api/datasets")
    assert resp.status_code == 200
    assert any(d["id"] == dataset_id for d in resp.json())


def test_schema_endpoint_and_override(client):
    upload = client.post("/api/datasets/upload", files={"file": ("small.csv", _small_csv_bytes(), "text/csv")})
    dataset_id = upload.json()["dataset_id"]

    schema_resp = client.get(f"/api/datasets/{dataset_id}/schema")
    assert schema_resp.status_code == 200
    mapping = schema_resp.json()["mapping"]
    assert mapping["vendor"] == "vendor"
    assert schema_resp.json()["confirmed"] is False

    override_resp = client.patch(
        f"/api/datasets/{dataset_id}/schema", json={"mapping": {**mapping, "vendor": "vendor"}}
    )
    assert override_resp.status_code == 200
    assert override_resp.json()["confirmed"] is True


def test_profile_endpoint(client):
    upload = client.post("/api/datasets/upload", files={"file": ("small.csv", _small_csv_bytes(), "text/csv")})
    dataset_id = upload.json()["dataset_id"]
    resp = client.get(f"/api/datasets/{dataset_id}/profile")
    assert resp.status_code == 200
    assert resp.json()["profile"]["row_count"] == 15


def test_full_adversarial_sample_triggers_all_15_rules_via_http(client):
    with open(SAMPLE_CSV, "rb") as f:
        upload = client.post(
            "/api/datasets/upload",
            files={"file": ("sample_payments.csv", f.read(), "text/csv")},
        )
    assert upload.status_code == 200
    dataset_id = upload.json()["dataset_id"]

    status = client.get(f"/api/jobs/{dataset_id}/status").json()
    assert status["status"] == "complete", status

    findings = client.get(f"/api/findings/dataset/{dataset_id}").json()
    triggered = {f["rule_id"] for f in findings}
    assert len(triggered) == 15
