from typing import Any

import pandas as pd

from app.services.audit_rules.base import AuditRule, row_snapshot


class BackdatedEntryRule(AuditRule):
    rule_id = "BACKDATED_ENTRY"
    rule_name = "Backdated Entry"
    severity = "HIGH"
    category = "timing_and_calendar"
    required_columns = ["date", "entry_date"]

    def evaluate(self, df: pd.DataFrame, config: dict[str, Any]) -> list[dict]:
        if not self.has_required_columns(df):
            return []

        threshold_days = config.get("backdated_threshold_days", 30)
        subset = df.dropna(subset=["date", "entry_date"])
        delta_days = (subset["entry_date"] - subset["date"]).dt.days
        bad_rows = subset[delta_days > threshold_days]
        if bad_rows.empty:
            return []

        flagged_rows = []
        for idx in bad_rows.index:
            snap = row_snapshot(df, idx)
            snap["days_backdated"] = int(delta_days.loc[idx])
            flagged_rows.append(snap)

        return [
            self.make_finding(
                flagged_rows=flagged_rows,
                supporting_metrics={
                    "backdated_count": len(flagged_rows),
                    "threshold_days": threshold_days,
                },
                audit_explanation=(
                    f"{len(flagged_rows)} entries were posted with a transaction date more than "
                    f"{threshold_days} days before the entry/document date. This pattern is "
                    f"consistent with backdating, which can be used to manipulate period-end results."
                ),
                trace={
                    "rule_file": "audit_rules/backdated_entry.py",
                    "fields_compared": ["date", "entry_date"],
                    "computation": f"(entry_date - date).days > {threshold_days}",
                },
            )
        ]
