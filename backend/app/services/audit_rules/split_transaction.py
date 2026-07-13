from typing import Any

import pandas as pd

from app.services.audit_rules.base import AuditRule, row_snapshot


class SplitTransactionRule(AuditRule):
    rule_id = "SPLIT_TRANSACTION"
    rule_name = "Split Transaction"
    severity = "HIGH"
    category = "amount_patterns"
    required_columns = ["vendor", "amount", "date"]

    def evaluate(self, df: pd.DataFrame, config: dict[str, Any], context: dict[str, Any]) -> list[dict]:
        if not self.has_required_columns(df):
            return []

        threshold = config.get("materiality_threshold") or config.get("MATERIALITY_THRESHOLD", 50000)
        min_group_size = config.get("split_transaction_min_rows", 2)

        subset = df.dropna(subset=self.required_columns)
        findings = []
        for (vendor, date), group in subset.groupby(["vendor", "date"]):
            if len(group) < min_group_size:
                continue
            total = group["amount"].sum()
            if total <= threshold:
                continue
            if total % 1 != 0 and total % 100 != 0:
                # only flag "round" aggregate totals as a split-transaction signature
                continue
            flagged_rows = [row_snapshot(df, idx) for idx in group.index]
            findings.append(
                self.make_finding(
                    flagged_rows=flagged_rows,
                    supporting_metrics={
                        "vendor": vendor,
                        "date": str(date),
                        "transaction_count": len(group),
                        "total_amount": float(total),
                        "threshold": threshold,
                    },
                    audit_explanation=(
                        f"Vendor {vendor} had {len(group)} separate transactions on {date} "
                        f"summing to {total}, a round total exceeding the materiality threshold "
                        f"of {threshold}. This pattern is consistent with structuring/splitting "
                        f"a single transaction to avoid an approval threshold."
                    ),
                    trace={
                        "rule_file": "audit_rules/split_transaction.py",
                        "fields_compared": ["vendor", "amount", "date"],
                        "computation": "GROUP BY vendor, date HAVING SUM(amount) round AND > threshold",
                    },
                )
            )
        return findings
