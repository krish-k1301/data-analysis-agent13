from typing import Any

import pandas as pd

from app.services.audit_rules.base import AuditRule, row_snapshot


class WeekendPostingRule(AuditRule):
    rule_id = "WEEKEND_POSTING"
    rule_name = "Weekend Posting"
    severity = "MEDIUM"
    category = "timing_and_calendar"
    required_columns = ["date"]

    def evaluate(self, df: pd.DataFrame, config: dict[str, Any], context: dict[str, Any]) -> list[dict]:
        if not self.has_required_columns(df):
            return []

        subset = df.dropna(subset=["date"])
        weekend_mask = subset["date"].dt.dayofweek >= 5
        bad_rows = subset[weekend_mask]
        if bad_rows.empty:
            return []

        flagged_rows = [row_snapshot(df, idx) for idx in bad_rows.index]
        return [
            self.make_finding(
                flagged_rows=flagged_rows,
                supporting_metrics={"weekend_entry_count": len(flagged_rows)},
                audit_explanation=(
                    f"{len(flagged_rows)} transaction(s) were posted on a Saturday or Sunday. "
                    f"Weekend postings fall outside normal business operations and warrant review."
                ),
                trace={
                    "rule_file": "audit_rules/weekend_posting.py",
                    "fields_compared": ["date"],
                    "computation": "date.dayofweek in {Saturday, Sunday}",
                },
            )
        ]
