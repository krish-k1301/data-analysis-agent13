from typing import Any

import pandas as pd

from app.services.audit_rules.base import AuditRule, row_snapshot


class DormantVendorRule(AuditRule):
    rule_id = "DORMANT_VENDOR"
    rule_name = "Dormant Vendor Reactivation"
    severity = "HIGH"
    category = "vendor_behaviour"
    required_columns = ["vendor", "date"]

    def evaluate(self, df: pd.DataFrame, config: dict[str, Any], context: dict[str, Any]) -> list[dict]:
        if not self.has_required_columns(df):
            return []

        dormant_days = config.get("dormant_vendor_days", 180)
        subset = df.dropna(subset=["vendor", "date"]).sort_values("date")

        flagged_rows = []
        for vendor, group in subset.groupby("vendor"):
            dates = group["date"]
            gaps = dates.diff().dt.days
            reactivation_idx = gaps[gaps > dormant_days].index
            for idx in reactivation_idx:
                snap = row_snapshot(df, idx)
                snap["days_dormant"] = int(gaps.loc[idx])
                flagged_rows.append(snap)

        if not flagged_rows:
            return []

        return [
            self.make_finding(
                flagged_rows=flagged_rows,
                supporting_metrics={
                    "reactivation_count": len(flagged_rows),
                    "dormant_days_threshold": dormant_days,
                },
                audit_explanation=(
                    f"{len(flagged_rows)} transaction(s) reactivate a vendor after more than "
                    f"{dormant_days} days of inactivity. Reactivated dormant vendors are a common "
                    f"indicator of shell-vendor or fictitious-vendor fraud schemes."
                ),
                trace={
                    "rule_file": "audit_rules/dormant_vendor.py",
                    "fields_compared": ["vendor", "date"],
                    "computation": f"gap between consecutive transactions per vendor > {dormant_days} days",
                },
            )
        ]
