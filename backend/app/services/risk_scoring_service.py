from typing import Any

from app.services.audit_rules.base import SEVERITY_BASE_SCORE


def _boost_for_metrics(metrics: dict[str, Any], config: dict[str, Any]) -> float:
    boost = 0.0
    threshold = config.get("materiality_threshold") or config.get("MATERIALITY_THRESHOLD", 50000)

    if "total_exposure" in metrics and threshold:
        ratio = metrics["total_exposure"] / threshold
        boost += min(10.0, ratio * 5)

    if "duplicate_count" in metrics:
        boost += min(5.0, max(0, metrics["duplicate_count"] - 2) * 2)

    if "p_value" in metrics and metrics["p_value"] < 0.05:
        boost += min(10.0, (0.05 - metrics["p_value"]) * 100)

    if "concentration_pct" in metrics:
        boost += min(10.0, max(0, metrics["concentration_pct"] - metrics.get("threshold_pct", 40)) / 2)

    if "gap_pct" in metrics:
        boost += min(10.0, max(0, metrics["gap_pct"] - 5) / 2)

    return boost


def score_finding(finding: dict[str, Any], statistics: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    base = SEVERITY_BASE_SCORE.get(finding.get("severity", "MEDIUM"), 50)
    boost = _boost_for_metrics(finding.get("supporting_metrics", {}), config)
    score = max(0, min(100, round(base + boost)))

    finding["risk_score"] = int(score)
    finding["risk_justification"] = (
        f"{finding.get('severity', 'MEDIUM')} severity finding for rule "
        f"'{finding.get('rule_name', finding.get('rule_id'))}' "
        f"affecting {len(finding.get('flagged_rows', []))} row(s); "
        f"base score {base} adjusted by {boost:+.1f} based on supporting metrics."
    )
    return finding


def score_findings(findings: list[dict[str, Any]], statistics: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    return [score_finding(f, statistics, config) for f in findings]
