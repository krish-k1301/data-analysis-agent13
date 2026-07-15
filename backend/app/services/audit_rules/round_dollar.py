from typing import Any

import pandas as pd

from app.services.audit_rules.base import AuditRule, row_snapshot


class RoundDollarRule(AuditRule):
    rule_id = "ROUND_DOLLAR"
    rule_name = "Round-Dollar Amount"
    severity = "LOW"
    category = "amount_patterns"
    required_columns = ["amount"]

    def evaluate(self, df: pd.DataFrame, config: dict[str, Any]) -> list[dict]:
        if not self.has_required_columns(df):
            return []

        min_amount = config.get("round_dollar_min_amount", 1000)
        subset = df.dropna(subset=["amount"])
        mask = (subset["amount"] % 1 == 0) & (subset["amount"].abs() > min_amount)
        bad_rows = subset[mask]
        if bad_rows.empty:
            return []

        flagged_rows = [row_snapshot(df, idx) for idx in bad_rows.index]
        return [
            self.make_finding(
                flagged_rows=flagged_rows,
                supporting_metrics={
                    "round_dollar_count": len(flagged_rows),
                    "min_amount": min_amount,
                },
                audit_explanation=(
                    f"{len(flagged_rows)} transaction(s) above {min_amount} are exact round-dollar "
                    f"amounts (no cents). Round-dollar amounts above materiality are a common "
                    f"indicator of estimated, fabricated, or manually-keyed entries."
                ),
                trace={
                    "rule_file": "audit_rules/round_dollar.py",
                    "fields_compared": ["amount"],
                    "computation": f"amount % 1 == 0 AND abs(amount) > {min_amount}",
                },
            )
        ]
