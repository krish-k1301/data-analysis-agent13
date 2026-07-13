from typing import Any

import pandas as pd

from app.services.audit_rules.base import AuditRule, row_snapshot


class AfterHoursEntryRule(AuditRule):
    rule_id = "AFTER_HOURS_ENTRY"
    rule_name = "After-Hours Entry"
    severity = "MEDIUM"
    category = "timing_and_calendar"
    required_columns = ["timestamp"]

    def evaluate(self, df: pd.DataFrame, config: dict[str, Any], context: dict[str, Any]) -> list[dict]:
        if not self.has_required_columns(df):
            return []

        start_hour = config.get("business_hours_start", 7)
        end_hour = config.get("business_hours_end", 19)

        subset = df.dropna(subset=["timestamp"])
        hours = subset["timestamp"].dt.hour
        mask = (hours < start_hour) | (hours >= end_hour)
        bad_rows = subset[mask]
        if bad_rows.empty:
            return []

        flagged_rows = [row_snapshot(df, idx) for idx in bad_rows.index]
        return [
            self.make_finding(
                flagged_rows=flagged_rows,
                supporting_metrics={
                    "after_hours_count": len(flagged_rows),
                    "business_hours": f"{start_hour:02d}:00-{end_hour:02d}:00",
                },
                audit_explanation=(
                    f"{len(flagged_rows)} entries were recorded outside business hours "
                    f"({start_hour:02d}:00-{end_hour:02d}:00). After-hours activity may "
                    f"indicate unauthorized access or unusual processing."
                ),
                trace={
                    "rule_file": "audit_rules/after_hours_entry.py",
                    "fields_compared": ["timestamp"],
                    "computation": f"hour not in [{start_hour}, {end_hour})",
                },
            )
        ]
