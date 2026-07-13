from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

SEVERITY_BASE_SCORE = {"HIGH": 85, "MEDIUM": 60, "LOW": 30}


class AuditRule(ABC):
    rule_id: str
    rule_name: str
    severity: str
    category: str
    required_columns: list[str] = []

    def has_required_columns(self, df: pd.DataFrame) -> bool:
        return all(col in df.columns and df[col].notna().any() for col in self.required_columns)

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, config: dict[str, Any], context: dict[str, Any]) -> list[dict]:
        """Return a list of raw finding dicts (no dataset_id/finding_id/risk_score yet)."""
        raise NotImplementedError

    def make_finding(
        self,
        flagged_rows: list[dict],
        supporting_metrics: dict,
        audit_explanation: str,
        trace: dict,
        severity: str | None = None,
    ) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": severity or self.severity,
            "flagged_rows": flagged_rows,
            "supporting_metrics": supporting_metrics,
            "audit_explanation": audit_explanation,
            "trace": trace,
        }


def row_snapshot(df: pd.DataFrame, idx: int, extra_cols: list[str] | None = None) -> dict:
    """Build a compact flagged-row dict: row_index + canonical fields present."""
    canonical = ["invoice_no", "vendor", "amount", "date", "entry_date", "timestamp"]
    cols = canonical + (extra_cols or [])
    row = df.loc[idx]
    out: dict[str, Any] = {"row_index": int(idx)}
    for col in cols:
        if col in df.columns:
            val = row[col]
            if pd.isna(val):
                continue
            if isinstance(val, pd.Timestamp):
                out[col] = val.isoformat()
            elif hasattr(val, "item"):
                out[col] = val.item()
            else:
                out[col] = val
    return out
