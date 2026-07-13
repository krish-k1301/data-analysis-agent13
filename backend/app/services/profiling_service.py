import pandas as pd


def _column_type(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    return "text"


def profile_dataframe(df: pd.DataFrame) -> dict:
    """Produce a per-column profile: dtype, completeness, cardinality,
    and basic distribution stats where applicable.
    """
    row_count = len(df)
    columns: dict[str, dict] = {}

    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())
        non_null = series.dropna()
        col_type = _column_type(series)

        entry: dict = {
            "type": col_type,
            "null_count": null_count,
            "null_pct": round((null_count / row_count) * 100, 2) if row_count else 0.0,
            "unique_count": int(non_null.nunique()),
            "sample_values": [str(v) for v in non_null.head(5).tolist()],
        }

        if col_type == "numeric" and not non_null.empty:
            entry.update(
                {
                    "mean": float(non_null.mean()),
                    "median": float(non_null.median()),
                    "std": float(non_null.std()) if len(non_null) > 1 else 0.0,
                    "min": float(non_null.min()),
                    "max": float(non_null.max()),
                }
            )
        elif col_type == "date" and not non_null.empty:
            entry.update(
                {
                    "min_date": non_null.min().isoformat(),
                    "max_date": non_null.max().isoformat(),
                }
            )

        columns[col] = entry

    total_cells = row_count * len(df.columns) if row_count else 0
    total_nulls = sum(c["null_count"] for c in columns.values())
    completeness_pct = round(100 - (total_nulls / total_cells * 100), 2) if total_cells else 0.0

    return {
        "row_count": row_count,
        "column_count": len(df.columns),
        "completeness_pct": completeness_pct,
        "columns": columns,
    }
