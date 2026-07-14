from app.services.risk_scoring_service import score_finding, score_findings


def _finding(severity: str, metrics: dict | None = None) -> dict:
    return {
        "severity": severity,
        "rule_name": "X",
        "supporting_metrics": metrics or {},
        "flagged_rows": [],
    }


def test_base_scores_by_severity():
    for severity, base in [("HIGH", 85), ("MEDIUM", 60), ("LOW", 30)]:
        scored = score_finding(_finding(severity), {}, {})
        assert scored["risk_score"] == base


def test_score_bounded_0_to_100_even_with_extreme_metrics():
    finding = _finding(
        "HIGH",
        {
            "total_exposure": 10_000_000,
            "duplicate_count": 50,
            "p_value": 0.0001,
            "concentration_pct": 99,
            "threshold_pct": 40,
            "gap_pct": 99,
        },
    )
    scored = score_finding(finding, {}, {"materiality_threshold": 1})
    assert 0 <= scored["risk_score"] <= 100


def test_score_never_negative_for_low_severity_no_metrics():
    scored = score_finding(_finding("LOW"), {}, {})
    assert scored["risk_score"] >= 0


def test_unknown_severity_defaults_to_medium_base():
    scored = score_finding(_finding("SOMETHING_UNEXPECTED"), {}, {})
    assert scored["risk_score"] == 50


def test_score_findings_batch_all_get_scored():
    findings = [_finding("HIGH"), _finding("LOW")]
    scored = score_findings(findings, {}, {})
    assert len(scored) == 2
    assert all("risk_justification" in f and isinstance(f["risk_score"], int) for f in scored)


def test_duplicate_count_boost_increases_score_monotonically():
    low = score_finding(_finding("HIGH", {"duplicate_count": 2}), {}, {})
    high = score_finding(_finding("HIGH", {"duplicate_count": 10}), {}, {})
    assert high["risk_score"] >= low["risk_score"]
