from typing import Any

import pandas as pd

from app.services.audit_rules.base import AuditRule


class SingleVendorConcentrationRule(AuditRule):
    rule_id = "SINGLE_VENDOR_CONCENTRATION"
    rule_name = "Single Vendor Spend Concentration"
    severity = "MEDIUM"
    category = "vendor_behaviour"
    required_columns = ["vendor", "amount"]

    def evaluate(self, df: pd.DataFrame, config: dict[str, Any]) -> list[dict]:
        if not self.has_required_columns(df):
            return []

        concentration_pct_threshold = config.get("vendor_concentration_pct", 40)
        subset = df.dropna(subset=self.required_columns)
        if subset.empty:
            return []

        total_spend = subset["amount"].abs().sum()
        if total_spend == 0:
            return []

        by_vendor = subset.groupby("vendor")["amount"].apply(lambda s: s.abs().sum())
        by_vendor_pct = (by_vendor / total_spend * 100).sort_values(ascending=False)

        breaches = by_vendor_pct[by_vendor_pct > concentration_pct_threshold]
        if breaches.empty:
            return []

        findings = []
        for vendor, pct in breaches.items():
            findings.append(
                self.make_finding(
                    flagged_rows=[],
                    supporting_metrics={
                        "vendor": vendor,
                        "vendor_spend": float(by_vendor[vendor]),
                        "total_spend": float(total_spend),
                        "concentration_pct": round(float(pct), 2),
                        "threshold_pct": concentration_pct_threshold,
                    },
                    audit_explanation=(
                        f"Vendor {vendor} accounts for {pct:.1f}% of total spend "
                        f"({by_vendor[vendor]:,.2f} of {total_spend:,.2f}), exceeding the "
                        f"{concentration_pct_threshold}% concentration threshold. High vendor "
                        f"concentration increases dependency risk and warrants review of "
                        f"procurement controls and vendor independence."
                    ),
                    trace={
                        "rule_file": "audit_rules/single_vendor_concentration.py",
                        "fields_compared": ["vendor", "amount"],
                        "computation": f"SUM(abs(amount)) per vendor / total_spend > {concentration_pct_threshold}%",
                    },
                )
            )
        return findings
