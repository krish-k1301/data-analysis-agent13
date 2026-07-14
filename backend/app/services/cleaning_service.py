import re

import numpy as np
import pandas as pd

from app.services.upload_service import sanitize_formula_injection

NULL_TOKENS = {"", "na", "n/a", "null", "none", "nan", "-", "--"}

_NUMERIC_RE = re.compile(r"^\(?-?\$?\s?[\d,]+\.?\d*\)?%?$")


def _is_text_column(series: pd.Series) -> bool:
    """True for raw text/object columns. Deliberately dtype-based rather than
    `pd.api.types.is_string_dtype`, which content-infers and returns False for
    an object-dtype column containing even one null — since ingestion loads
    every column via `dtype=str`, virtually every real column has nulls, so
    that check silently skipped whitespace-stripping/null-normalization/type
    coercion for almost all data (see memory: windows-server-env-gotchas).
    """
    return pd.api.types.is_object_dtype(series) or isinstance(series.dtype, pd.StringDtype)


def _looks_numeric(series: pd.Series, threshold: float = 0.8) -> bool:
    non_null = series.dropna()
    if non_null.empty:
        return False
    matches = non_null.astype(str).str.strip().str.match(_NUMERIC_RE)
    return matches.mean() >= threshold


def _coerce_numeric(series: pd.Series) -> pd.Series:
    def parse(v):
        if pd.isna(v):
            return np.nan
        s = str(v).strip()
        if not s:
            return np.nan
        negative = s.startswith("(") and s.endswith(")")
        s = s.strip("()")
        s = s.replace("$", "").replace(",", "").replace("%", "").strip()
        try:
            val = float(s)
        except ValueError:
            return np.nan
        return -val if negative else val

    return series.apply(parse)


def _looks_date(series: pd.Series, threshold: float = 0.8) -> bool:
    non_null = series.dropna()
    if non_null.empty:
        return False
    sample = non_null.astype(str).str.strip()
    if len(sample) > 200:
        sample = sample.sample(200, random_state=0)
    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    return parsed.notna().mean() >= threshold


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Clean a raw DataFrame: whitespace, null normalization, type coercion,
    dedup, formula-injection sanitization. Returns (cleaned_df, cleaning_log).
    """
    log: list[dict] = []
    df = df.copy()

    # 1. Strip whitespace + sanitize formula injection on string cells
    for col in df.columns:
        if _is_text_column(df[col]):
            df[col] = df[col].apply(
                lambda v: sanitize_formula_injection(v.strip()) if isinstance(v, str) else v
            )

    # 2. Normalize null tokens
    null_replacements = 0

    def _normalize_null(v):
        nonlocal null_replacements
        if isinstance(v, str) and v.strip().lower() in NULL_TOKENS:
            null_replacements += 1
            return np.nan
        return v

    for col in df.columns:
        if _is_text_column(df[col]):
            df[col] = df[col].apply(_normalize_null)
    if null_replacements:
        log.append({"step": "normalize_nulls", "count": null_replacements})

    # 3. Drop exact duplicate rows
    before = len(df)
    df = df.drop_duplicates()
    dropped = before - len(df)
    if dropped:
        log.append({"step": "drop_duplicate_rows", "count": dropped})
    df = df.reset_index(drop=True)

    # 4. Type coercion: numeric-looking and date-looking columns
    for col in df.columns:
        if not _is_text_column(df[col]):
            continue
        if _looks_numeric(df[col]):
            coerced = _coerce_numeric(df[col])
            df[col] = coerced
            log.append({"step": "coerce_numeric", "column": col})
        elif _looks_date(df[col]):
            parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
            df[col] = parsed
            log.append({"step": "coerce_date", "column": col})

    return df, log
