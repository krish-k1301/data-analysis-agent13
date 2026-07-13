from typing import Any

import pandas as pd

from app.services.audit_rules.base import AuditRule, row_snapshot

# Configurable list of fixed-date US public holidays (MM-DD). Movable holidays
# (Thanksgiving, etc.) are intentionally excluded from this MVP heuristic.
DEFAULT_HOLIDAYS_MMDD = {
    "01-01",  # New Year's Day
    "07-04",  # Independence Day
    "12-25",  # Christmas Day
    "11-11",  # Veterans Day
    "06-19",  # Juneteenth
}


class PublicHolidayPostingRule(AuditRule):
    rule_id = "PUBLIC_HOLIDAY_POSTING"
    rule_name = "Public Holiday Posting"
    severity = "MEDIUM"
    category = "timing_and_calendar"
    required_columns = ["date"]

    def evaluate(self, df: pd.DataFrame, config: dict[str, Any], context: dict[str, Any]) -> list[dict]:
        if not self.has_required_columns(df):
            return []

        holidays = set(config.get("public_holidays_mmdd", DEFAULT_HOLIDAYS_MMDD))
        subset = df.dropna(subset=["date"])
        mmdd = subset["date"].dt.strftime("%m-%d")
        bad_rows = subset[mmdd.isin(holidays)]
        if bad_rows.empty:
            return []

        flagged_rows = [row_snapshot(df, idx) for idx in bad_rows.index]
        return [
            self.make_finding(
                flagged_rows=flagged_rows,
                supporting_metrics={"holiday_entry_count": len(flagged_rows)},
                audit_explanation=(
                    f"{len(flagged_rows)} transaction(s) were posted on a recognized public "
                    f"holiday. Entries on non-business days may indicate manual overrides "
                    f"or backdated postings."
                ),
                trace={
                    "rule_file": "audit_rules/public_holiday_posting.py",
                    "fields_compared": ["date"],
                    "computation": "date.strftime('%m-%d') in configured holiday list",
                },
            )
        ]
