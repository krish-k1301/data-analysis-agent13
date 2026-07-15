from typing import Any

import pandas as pd

from app.services.audit_rules.base import AuditRule, row_snapshot

CHECKED_FIELDS = ["vendor", "amount", "date", "invoice_no"]


class MissingRequiredFieldRule(AuditRule):
    rule_id = "MISSING_REQUIRED_FIELD"
    rule_name = "Missing Required Field"
    severity = "MEDIUM"
    category = "duplicate_and_completeness"
    required_columns = []  # dynamic: at least one of CHECKED_FIELDS must be mapped

    def evaluate(self, df: pd.DataFrame, config: dict[str, Any]) -> list[dict]:
        present_fields = [f for f in CHECKED_FIELDS if f in df.columns]
        if not present_fields:
            return []

        mask = df[present_fields].isna().any(axis=1)
        bad_rows = df[mask]
        if bad_rows.empty:
            return []

        flagged_rows = []
        for idx in bad_rows.index:
            missing = [f for f in present_fields if pd.isna(df.loc[idx, f])]
            snap = row_snapshot(df, idx)
            snap["missing_fields"] = missing
            flagged_rows.append(snap)

        return [
            self.make_finding(
                flagged_rows=flagged_rows,
                supporting_metrics={
                    "checked_fields": present_fields,
                    "affected_row_count": len(flagged_rows),
                },
                audit_explanation=(
                    f"{len(flagged_rows)} row(s) are missing at least one required field "
                    f"among {present_fields}. Incomplete records reduce traceability and may "
                    f"indicate data entry control weaknesses."
                ),
                trace={
                    "rule_file": "audit_rules/missing_required_field.py",
                    "fields_compared": present_fields,
                    "computation": "any(field is null for field in checked_fields)",
                },
            )
        ]
