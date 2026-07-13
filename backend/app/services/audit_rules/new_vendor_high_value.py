from typing import Any

import pandas as pd

from app.services.audit_rules.base import AuditRule, row_snapshot


class NewVendorHighValueRule(AuditRule):
    rule_id = "NEW_VENDOR_HIGH_VALUE"
    rule_name = "New Vendor High-Value Transaction"
    severity = "HIGH"
    category = "vendor_behaviour"
    required_columns = ["vendor", "date", "amount"]

    def evaluate(self, df: pd.DataFrame, config: dict[str, Any], context: dict[str, Any]) -> list[dict]:
        if not self.has_required_columns(df):
            return []

        window_days = config.get("new_vendor_window_days", 30)
        high_value = config.get("new_vendor_high_value", 10000)

        subset = df.dropna(subset=self.required_columns).sort_values("date")
        first_seen = subset.groupby("vendor")["date"].transform("min")
        days_since_first = (subset["date"] - first_seen).dt.days

        mask = (days_since_first <= window_days) & (subset["amount"].abs() > high_value)
        bad_rows = subset[mask]
        if bad_rows.empty:
            return []

        flagged_rows = []
        for idx in bad_rows.index:
            snap = row_snapshot(df, idx)
            snap["days_since_first_transaction"] = int(days_since_first.loc[idx])
            flagged_rows.append(snap)

        return [
            self.make_finding(
                flagged_rows=flagged_rows,
                supporting_metrics={
                    "flagged_count": len(flagged_rows),
                    "window_days": window_days,
                    "high_value_threshold": high_value,
                },
                audit_explanation=(
                    f"{len(flagged_rows)} transaction(s) exceed {high_value} from a vendor that "
                    f"first appeared within the prior {window_days} days. New vendors transacting "
                    f"at high value shortly after onboarding warrant vendor master-file verification."
                ),
                trace={
                    "rule_file": "audit_rules/new_vendor_high_value.py",
                    "fields_compared": ["vendor", "date", "amount"],
                    "computation": f"days_since_first_transaction <= {window_days} AND abs(amount) > {high_value}",
                },
            )
        ]
