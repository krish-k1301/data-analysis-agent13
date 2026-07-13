from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from app.services.audit_rules.base import AuditRule

BENFORD_EXPECTED = {d: np.log10(1 + 1 / d) for d in range(1, 10)}


class BenfordsLawRule(AuditRule):
    rule_id = "BENFORDS_LAW"
    rule_name = "Benford's Law Deviation"
    severity = "MEDIUM"
    category = "amount_patterns"
    required_columns = ["amount"]

    def evaluate(self, df: pd.DataFrame, config: dict[str, Any], context: dict[str, Any]) -> list[dict]:
        if not self.has_required_columns(df):
            return []

        p_threshold = config.get("benford_p_value", 0.05)
        amounts = df["amount"].dropna()
        amounts = amounts[amounts > 0]
        if len(amounts) < 100:
            return []  # corpus too small for a reliable chi-squared test

        first_digits = amounts.apply(lambda v: int(str(v).lstrip("0.").replace(".", "")[0]))
        first_digits = first_digits[(first_digits >= 1) & (first_digits <= 9)]
        observed_counts = first_digits.value_counts().reindex(range(1, 10), fill_value=0).sort_index()

        total = observed_counts.sum()
        expected_counts = np.array([BENFORD_EXPECTED[d] * total for d in range(1, 10)])

        chi2, p_value = stats.chisquare(f_obs=observed_counts.values, f_exp=expected_counts)

        if p_value >= p_threshold:
            return []  # distribution is consistent with Benford's Law

        observed_pct = (observed_counts / total * 100).round(2).to_dict()
        expected_pct = {d: round(BENFORD_EXPECTED[d] * 100, 2) for d in range(1, 10)}

        return [
            self.make_finding(
                flagged_rows=[],
                supporting_metrics={
                    "chi_squared": float(chi2),
                    "p_value": float(p_value),
                    "sample_size": int(total),
                    "observed_pct_by_first_digit": observed_pct,
                    "expected_pct_by_first_digit": expected_pct,
                },
                audit_explanation=(
                    f"The first-digit distribution of {total} amount values deviates significantly "
                    f"from Benford's Law (chi-squared={chi2:.2f}, p={p_value:.4f} < {p_threshold}). "
                    f"This may indicate fabricated, estimated, or manipulated figures across the "
                    f"dataset and warrants further sampling."
                ),
                trace={
                    "rule_file": "audit_rules/benfords_law.py",
                    "fields_compared": ["amount"],
                    "computation": "chi-squared goodness-of-fit vs Benford's expected first-digit distribution",
                },
            )
        ]
