from typing import Any

import pandas as pd

from app.services.audit_rules.base import AuditRule, row_snapshot


class DuplicatePaymentRule(AuditRule):
    rule_id = "DUPLICATE_PAYMENT"
    rule_name = "Duplicate Payment (Same Vendor/Amount, Different Invoice)"
    severity = "HIGH"
    category = "duplicate_and_completeness"
    required_columns = ["vendor", "amount", "date"]

    def evaluate(self, df: pd.DataFrame, config: dict[str, Any], context: dict[str, Any]) -> list[dict]:
        if not self.has_required_columns(df):
            return []

        window_days = config.get("duplicate_payment_window_days", 7)
        subset = df.dropna(subset=self.required_columns)
        if subset.empty:
            return []

        findings = []
        seen_pairs: set[tuple] = set()

        for (vendor, amount), group in subset.groupby(["vendor", "amount"]):
            if len(group) < 2:
                continue
            group = group.sort_values("date")
            rows = list(group.index)
            for i in range(len(rows)):
                for j in range(i + 1, len(rows)):
                    idx_a, idx_b = rows[i], rows[j]
                    date_a, date_b = df.loc[idx_a, "date"], df.loc[idx_b, "date"]
                    delta = abs((date_b - date_a).days)
                    if delta > window_days:
                        continue
                    inv_a = df.loc[idx_a, "invoice_no"] if "invoice_no" in df.columns else None
                    inv_b = df.loc[idx_b, "invoice_no"] if "invoice_no" in df.columns else None
                    if inv_a is not None and inv_b is not None and inv_a == inv_b:
                        continue  # same invoice -> handled by DUPLICATE_INVOICE
                    pair_key = (idx_a, idx_b)
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)
                    findings.append(
                        self.make_finding(
                            flagged_rows=[row_snapshot(df, idx_a), row_snapshot(df, idx_b)],
                            supporting_metrics={
                                "vendor": vendor,
                                "amount": float(amount),
                                "days_apart": delta,
                            },
                            audit_explanation=(
                                f"Two payments of the same amount ({amount}) were made to vendor "
                                f"{vendor} within {delta} day(s) of each other under different "
                                f"invoice numbers. This pattern is consistent with a duplicate "
                                f"payment control failure."
                            ),
                            trace={
                                "rule_file": "audit_rules/duplicate_payment.py",
                                "fields_compared": ["vendor", "amount", "date", "invoice_no"],
                                "computation": f"same vendor+amount, date delta <= {window_days} days, different invoice_no",
                            },
                        )
                    )
        return findings
