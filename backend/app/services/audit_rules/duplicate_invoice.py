from typing import Any

import pandas as pd

from app.services.audit_rules.base import AuditRule, row_snapshot


class DuplicateInvoiceRule(AuditRule):
    rule_id = "DUPLICATE_INVOICE"
    rule_name = "Duplicate Invoice Number"
    severity = "HIGH"
    category = "duplicate_and_completeness"
    required_columns = ["invoice_no", "vendor", "amount", "date"]

    def evaluate(self, df: pd.DataFrame, config: dict[str, Any], context: dict[str, Any]) -> list[dict]:
        if not self.has_required_columns(df):
            return []

        subset = df.dropna(subset=self.required_columns)
        if subset.empty:
            return []

        groups = subset.groupby(["invoice_no", "vendor", "amount", "date"])
        findings = []
        for key, group in groups:
            if len(group) < 2:
                continue
            invoice_no, vendor, amount, date = key
            flagged_rows = [row_snapshot(df, idx) for idx in group.index]
            total_exposure = float(amount) * (len(group) - 1)
            findings.append(
                self.make_finding(
                    flagged_rows=flagged_rows,
                    supporting_metrics={
                        "duplicate_count": len(group),
                        "total_exposure": total_exposure,
                        "amount": float(amount),
                    },
                    audit_explanation=(
                        f"Invoice {invoice_no} was posted {len(group)} times to vendor {vendor} "
                        f"for the same amount ({amount}) on {date}. No distinguishing reversal or "
                        f"credit note is present in the dataset. Total exposure: {total_exposure}."
                    ),
                    trace={
                        "rule_file": "audit_rules/duplicate_invoice.py",
                        "fields_compared": ["invoice_no", "vendor", "amount", "date"],
                        "computation": "GROUP BY invoice_no, vendor, amount, date HAVING COUNT(*) > 1",
                    },
                )
            )
        return findings
