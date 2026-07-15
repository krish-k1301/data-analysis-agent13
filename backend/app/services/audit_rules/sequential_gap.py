import re
from typing import Any

import pandas as pd

from app.services.audit_rules.base import AuditRule


class SequentialGapRule(AuditRule):
    rule_id = "SEQUENTIAL_GAP"
    rule_name = "Sequential Invoice Number Gap"
    severity = "MEDIUM"
    category = "duplicate_and_completeness"
    required_columns = ["invoice_no"]

    def evaluate(self, df: pd.DataFrame, config: dict[str, Any]) -> list[dict]:
        if not self.has_required_columns(df):
            return []

        def extract_numeric(v):
            if pd.isna(v):
                return None
            match = re.search(r"\d+", str(v))
            return int(match.group()) if match else None

        # Use a plain Python list, not Series.apply(): apply() infers a
        # dtype for the result, and mixing int with None commonly upcasts
        # to float64 (None -> NaN). NaN then passes an `is not None` check
        # (float('nan') is not None), silently corrupting the int sequence
        # and crashing range() below with a non-integer bound.
        extracted = [extract_numeric(v) for v in df["invoice_no"].tolist()]
        numbers = sorted({n for n in extracted if n is not None})
        if len(numbers) < 10:
            return []

        expected_count = numbers[-1] - numbers[0] + 1
        actual_count = len(numbers)
        missing_count = expected_count - actual_count
        gap_pct = (missing_count / expected_count) * 100 if expected_count else 0

        if gap_pct <= 5:
            return []

        present = set(numbers)
        missing_numbers = [n for n in range(numbers[0], numbers[-1] + 1) if n not in present]

        return [
            self.make_finding(
                flagged_rows=[],
                supporting_metrics={
                    "expected_count": expected_count,
                    "actual_count": actual_count,
                    "missing_count": missing_count,
                    "gap_pct": round(gap_pct, 2),
                    "sample_missing": missing_numbers[:25],
                },
                audit_explanation=(
                    f"Invoice numbering sequence spans {numbers[0]}-{numbers[-1]} "
                    f"({expected_count} expected), but only {actual_count} were found "
                    f"({missing_count} missing, {gap_pct:.1f}% gap). Gaps above 5% may indicate "
                    f"unrecorded, voided, or off-books transactions."
                ),
                trace={
                    "rule_file": "audit_rules/sequential_gap.py",
                    "fields_compared": ["invoice_no"],
                    "computation": "numeric range coverage of invoice_no sequence",
                },
            )
        ]
