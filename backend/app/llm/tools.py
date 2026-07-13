from typing import Any

import pandas as pd

from app.services.duckdb_service import QueryValidationError, query_parquet

MAX_QUERY_ROWS = 50
MAX_TOOL_ITERATIONS = 3

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "query_dataset",
            "description": (
                "Run a read-only SQL SELECT query on the cleaned dataset. Use this to "
                "investigate specific patterns, filter data, or compute aggregates. "
                "The table is named 'dataset'. Results are capped at 50 rows."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": (
                            "A valid SQL SELECT query, e.g. "
                            "SELECT vendor, SUM(amount) FROM dataset GROUP BY vendor "
                            "ORDER BY SUM(amount) DESC LIMIT 10"
                        ),
                    }
                },
                "required": ["sql"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vendor_summary",
            "description": "Get aggregated statistics for a specific vendor: total spend, transaction count, average amount, date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vendor_id": {"type": "string", "description": "The vendor name/identifier as it appears in the dataset."}
                },
                "required": ["vendor_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_column_statistics",
            "description": "Get the statistical profile of a column: mean, median, std, min, max, quartiles, outlier count.",
            "parameters": {
                "type": "object",
                "properties": {
                    "column_name": {"type": "string", "description": "The column name to profile."}
                },
                "required": ["column_name"],
            },
        },
    },
]


def _handle_query_dataset(args: dict, context: dict) -> dict:
    try:
        columns, rows = query_parquet(context["parquet_path"], args["sql"], limit=MAX_QUERY_ROWS)
        return {"columns": columns, "rows": rows, "row_count": len(rows)}
    except QueryValidationError as e:
        return {"error": str(e)}


def _handle_get_vendor_summary(args: dict, context: dict) -> dict:
    df: pd.DataFrame = context["df"]
    vendor_id = args.get("vendor_id")
    if "vendor" not in df.columns:
        return {"error": "Dataset has no mapped 'vendor' column"}

    subset = df[df["vendor"].astype(str) == str(vendor_id)]
    if subset.empty:
        return {"error": f"No transactions found for vendor '{vendor_id}'"}

    result: dict[str, Any] = {"vendor_id": vendor_id, "transaction_count": int(len(subset))}
    if "amount" in subset.columns:
        amounts = subset["amount"].dropna()
        if not amounts.empty:
            result.update(
                {
                    "total_spend": float(amounts.sum()),
                    "avg_amount": float(amounts.mean()),
                    "min_amount": float(amounts.min()),
                    "max_amount": float(amounts.max()),
                }
            )
    if "date" in subset.columns:
        dates = subset["date"].dropna()
        if not dates.empty:
            result.update({"first_date": dates.min().isoformat(), "last_date": dates.max().isoformat()})

    return result


def _handle_get_column_statistics(args: dict, context: dict) -> dict:
    df: pd.DataFrame = context["df"]
    column_name = args.get("column_name")
    if column_name not in df.columns:
        return {"error": f"Column '{column_name}' not found in dataset"}

    series = df[column_name].dropna()
    if series.empty:
        return {"error": f"Column '{column_name}' has no non-null values"}

    if pd.api.types.is_numeric_dtype(series):
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        outliers = series[(series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)]
        return {
            "column": column_name,
            "mean": float(series.mean()),
            "median": float(series.median()),
            "std": float(series.std()) if len(series) > 1 else 0.0,
            "min": float(series.min()),
            "max": float(series.max()),
            "q1": float(q1),
            "q3": float(q3),
            "outlier_count": int(len(outliers)),
        }

    return {
        "column": column_name,
        "unique_count": int(series.nunique()),
        "top_values": series.value_counts().head(5).to_dict(),
    }


TOOL_HANDLERS = {
    "query_dataset": _handle_query_dataset,
    "get_vendor_summary": _handle_get_vendor_summary,
    "get_column_statistics": _handle_get_column_statistics,
}


def execute_tool(name: str, args: dict, context: dict) -> dict:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return {"error": f"Unknown tool '{name}'"}
    try:
        return handler(args, context)
    except Exception as e:  # noqa: BLE001 - tool failures should not crash the LLM loop
        return {"error": str(e)}
