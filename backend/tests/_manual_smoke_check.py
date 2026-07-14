"""Quick manual smoke test: run the engine end-to-end (bypassing FastAPI/DB)
against the adversarial sample_payments.csv to sanity-check the pipeline
before wiring up the API layer.
"""
import sys

from app.services import cleaning_service, ingestion_service, profiling_service, schema_service, statistics_service
from app.services.audit_rules import registry as rule_registry
from app.services.risk_scoring_service import score_findings

RAW_PATH = "sample_data/sample_payments.csv"


def main():
    df = ingestion_service.load_dataframe(RAW_PATH)
    print(f"[ingest] rows={len(df)} cols={len(df.columns)}")

    cleaned, log = cleaning_service.clean_dataframe(df)
    print(f"[clean] rows={len(cleaned)} log_steps={len(log)}")
    for entry in log:
        if entry["step"] in ("drop_duplicate_rows", "normalize_nulls"):
            print("  ", entry)

    profile = profiling_service.profile_dataframe(cleaned)
    print(f"[profile] completeness_pct={profile['completeness_pct']}")

    mapping = schema_service.infer_schema_mapping(cleaned)
    print(f"[schema_fit] mapping={mapping}")
    df_mapped = schema_service.apply_schema_mapping(cleaned, mapping)

    if len(df_mapped) < 10 or not mapping:
        print("VALIDATION FAILED")
        sys.exit(1)

    config = {
        "materiality_threshold": 50000,
        "MATERIALITY_THRESHOLD": 50000,
        "dormant_vendor_days": 180,
        "new_vendor_window_days": 30,
        "new_vendor_high_value": 10000,
        "vendor_concentration_pct": 40,
        "benford_p_value": 0.05,
        "outlier_zscore_threshold": 3.0,
    }

    findings = []
    for rule in rule_registry.get_enabled_rules(None):
        try:
            rule_findings = rule.evaluate(df_mapped, config, {"statistics": {}})
        except Exception as e:  # noqa: BLE001
            print(f"  RULE ERROR {rule.rule_id}: {e}")
            raise
        if rule_findings:
            print(f"  [{rule.rule_id}] -> {len(rule_findings)} finding(s)")
        findings.extend(rule_findings)

    stats = statistics_service.compute_statistics(df_mapped, config)
    print(f"[statistics] amount_count={stats['amount'].get('count')} "
          f"outliers_iqr={stats['amount'].get('outliers_iqr_count')} "
          f"vendor_trend_spikes={len(stats['vendor_trend_spikes'])}")

    scored = score_findings(findings, stats, config)
    print(f"[risk_score] total_findings={len(scored)}")

    triggered_rules = {f["rule_id"] for f in scored}
    all_rule_ids = set(rule_registry.ALL_RULE_IDS)
    missing = all_rule_ids - triggered_rules
    print(f"\nTotal findings: {len(scored)}")
    print(f"Rules triggered: {len(triggered_rules)}/{len(all_rule_ids)}")
    if missing:
        print(f"Rules NOT triggered (may be expected, verify): {sorted(missing)}")

    by_severity = {}
    for f in scored:
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
    print(f"By severity: {by_severity}")


if __name__ == "__main__":
    main()
