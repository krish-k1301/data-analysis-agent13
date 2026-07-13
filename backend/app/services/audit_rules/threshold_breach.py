from typing import Any

import pandas as pd

from app.services.audit_rules.base import AuditRule, row_snapshot


class ThresholdBreachRule(AuditRule):
    rule_id = "THRESHOLD_BREACH"
    rule_name = "Materiality Threshold Breach"
    severity = "HIGH"
    category = "amount_patterns"
    required_columns = ["amount"]

    def evaluate(self, df: pd.DataFrame, config: dict[str, Any], context: dict[str, Any]) -> list[dict]:
        if not self.has_required_columns(df):
            return []

        # Prefer a statistics-informed threshold if available (e.g. p99), else
        # fall back to the configured materiality threshold. This is the one
        # rule intentionally coupled to the statistics node's output, with a
        # graceful fallback so it still works if statistics is empty/missing.
        stats_threshold = None
        amount_stats = (context or {}).get("statistics", {}).get("amount", {})
        if isinstance(amount_stats, dict):
            stats_threshold = amount_stats.get("p99")

        threshold = config.get("materiality_threshold") or stats_threshold or config.get(
            "MATERIALITY_THRESHOLD", 50000
        )

        subset = df.dropna(subset=["amount"])
        bad_rows = subset[subset["amount"].abs() > threshold]
        if bad_rows.empty:
            return []

        flagged_rows = [row_snapshot(df, idx) for idx in bad_rows.index]
        return [
            self.make_finding(
                flagged_rows=flagged_rows,
                supporting_metrics={
                    "breach_count": len(flagged_rows),
                    "threshold": threshold,
                    "max_amount": float(bad_rows["amount"].abs().max()),
                },
                audit_explanation=(
                    f"{len(flagged_rows)} transaction(s) exceed the materiality threshold of "
                    f"{threshold}. High-value transactions warrant substantive testing and "
                    f"supporting documentation review."
                ),
                trace={
                    "rule_file": "audit_rules/threshold_breach.py",
                    "fields_compared": ["amount"],
                    "computation": f"abs(amount) > {threshold}",
                },
            )
        ]
