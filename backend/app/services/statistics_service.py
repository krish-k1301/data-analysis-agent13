from typing import Any

import pandas as pd

MAX_VENDORS_IN_TREND = 50


def _amount_stats(df: pd.DataFrame, config: dict[str, Any]) -> dict:
    if "amount" not in df.columns:
        return {}
    amounts = df["amount"].dropna()
    if amounts.empty:
        return {}

    zscore_threshold = config.get("outlier_zscore_threshold", 3.0)
    std = amounts.std()
    z = (amounts - amounts.mean()) / std if std else pd.Series([0] * len(amounts), index=amounts.index)
    z_outliers = amounts[z.abs() > zscore_threshold]

    q1, q3 = amounts.quantile(0.25), amounts.quantile(0.75)
    iqr = q3 - q1
    lower_fence, upper_fence = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    iqr_outliers = amounts[(amounts < lower_fence) | (amounts > upper_fence)]

    return {
        "count": int(len(amounts)),
        "mean": float(amounts.mean()),
        "median": float(amounts.median()),
        "std": float(std) if pd.notna(std) else 0.0,
        "min": float(amounts.min()),
        "max": float(amounts.max()),
        "p95": float(amounts.quantile(0.95)),
        "p99": float(amounts.quantile(0.99)),
        "skewness": float(amounts.skew()) if len(amounts) > 2 else 0.0,
        "kurtosis": float(amounts.kurtosis()) if len(amounts) > 3 else 0.0,
        "outliers_zscore_count": int(len(z_outliers)),
        "outliers_iqr_count": int(len(iqr_outliers)),
        "iqr_fence": {"lower": float(lower_fence), "upper": float(upper_fence)},
    }


def _vendor_trend(df: pd.DataFrame, config: dict[str, Any]) -> dict:
    required = {"vendor", "amount", "date"}
    if not required.issubset(df.columns):
        return {"trend": {}, "spikes": []}

    subset = df.dropna(subset=list(required)).copy()
    if subset.empty:
        return {"trend": {}, "spikes": []}

    subset["month"] = subset["date"].dt.to_period("M")
    monthly = subset.groupby(["vendor", "month"])["amount"].sum().reset_index()

    top_vendors = (
        subset.groupby("vendor")["amount"].apply(lambda s: s.abs().sum())
        .sort_values(ascending=False)
        .head(MAX_VENDORS_IN_TREND)
        .index
    )

    trend: dict[str, Any] = {}
    spikes: list[dict] = []
    for vendor, group in monthly[monthly["vendor"].isin(top_vendors)].groupby("vendor"):
        group = group.sort_values("month")
        pct_change = group["amount"].pct_change() * 100
        trend[str(vendor)] = {
            "months": [str(m) for m in group["month"]],
            "totals": [round(float(v), 2) for v in group["amount"]],
            "pct_change": [None if pd.isna(p) else round(float(p), 2) for p in pct_change],
        }
        for month, pct in zip(group["month"], pct_change):
            if pd.notna(pct) and abs(pct) > 50:
                spikes.append({"vendor": str(vendor), "month": str(month), "pct_change": round(float(pct), 2)})

    return {"trend": trend, "spikes": spikes}


def _vendor_variance(df: pd.DataFrame) -> dict:
    required = {"vendor", "amount"}
    if not required.issubset(df.columns):
        return {}
    subset = df.dropna(subset=list(required))
    if subset.empty:
        return {}
    overall_mean = subset["amount"].mean()
    by_vendor = subset.groupby("vendor")["amount"].mean().sort_values(ascending=False).head(MAX_VENDORS_IN_TREND)
    variance = {}
    for vendor, mean_val in by_vendor.items():
        deviation_pct = ((mean_val - overall_mean) / overall_mean * 100) if overall_mean else 0
        variance[str(vendor)] = {
            "vendor_mean": round(float(mean_val), 2),
            "overall_mean": round(float(overall_mean), 2),
            "deviation_pct": round(float(deviation_pct), 2),
        }
    return variance


def compute_statistics(df: pd.DataFrame, config: dict[str, Any] | None = None) -> dict:
    """Compute dataset-level statistical procedures: outlier detection
    (z-score + IQR), vendor trend (MoM), and vendor variance analysis.
    Benford's Law lives in audit_rules/benfords_law.py since it produces a
    Finding, not a statistics artifact.
    """
    config = config or {}
    trend = _vendor_trend(df, config)
    return {
        "amount": _amount_stats(df, config),
        "vendor_trend": trend["trend"],
        "vendor_trend_spikes": trend["spikes"],
        "vendor_variance": _vendor_variance(df),
    }
