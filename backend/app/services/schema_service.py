import pandas as pd

CANONICAL_ROLES = ["vendor", "amount", "date", "invoice_no", "entry_date", "timestamp"]

ROLE_KEYWORDS: dict[str, list[str]] = {
    "vendor": ["vendor", "supplier", "payee", "party", "merchant"],
    "amount": ["amount", "total", "value", "price", "cost", "sum", "net", "gross"],
    "date": ["date", "txn_date", "transaction_date", "posting_date", "post_date"],
    "invoice_no": ["invoice", "inv_no", "inv#", "doc_no", "document_number", "invoice_number", "invoice_no"],
    "entry_date": ["entry_date", "document_date", "created_date", "doc_date"],
    "timestamp": ["timestamp", "datetime", "time"],
}

REQUIRED_TYPE: dict[str, str] = {
    "vendor": "text",
    "amount": "numeric",
    "date": "date",
    "invoice_no": None,  # numeric or text
    "entry_date": "date",
    "timestamp": None,
}


def _column_type(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    return "text"


def infer_schema_mapping(df: pd.DataFrame) -> dict[str, str]:
    """Heuristically infer canonical role -> source column mapping using
    keyword matching on column names, gated by content-type compatibility.
    Returns only roles that found a confident match.
    """
    col_types = {col: _column_type(df[col]) for col in df.columns}

    # score[role][column] = keyword match strength
    candidates: dict[str, list[tuple[str, int]]] = {role: [] for role in CANONICAL_ROLES}

    for col in df.columns:
        col_norm = col.strip().lower().replace(" ", "_")
        for role, keywords in ROLE_KEYWORDS.items():
            required_type = REQUIRED_TYPE[role]
            if required_type and col_types[col] != required_type:
                # allow invoice_no-like numeric columns typed as numeric too
                continue
            for kw in keywords:
                if kw in col_norm:
                    score = 100 - abs(len(col_norm) - len(kw))  # prefer tighter match
                    if col_norm == kw:
                        score += 50
                    candidates[role].append((col, score))
                    break

    # Greedy assignment: highest score first, no column reused across roles
    all_scored = [
        (role, col, score)
        for role, cols in candidates.items()
        for col, score in cols
    ]
    all_scored.sort(key=lambda t: t[2], reverse=True)

    mapping: dict[str, str] = {}
    used_columns: set[str] = set()
    for role, col, _score in all_scored:
        if role in mapping or col in used_columns:
            continue
        mapping[role] = col
        used_columns.add(col)

    return mapping


def apply_schema_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Return a copy of df with canonical role columns added alongside the
    original columns (canonical columns are aliases, originals are kept).
    """
    df = df.copy()
    for role, source_col in mapping.items():
        if source_col in df.columns and role not in df.columns:
            df[role] = df[source_col]
    return df
