import os
import uuid

import pandas as pd


class IngestionError(Exception):
    pass


def load_dataframe(raw_path: str) -> pd.DataFrame:
    """Load a CSV or XLSX file into a pandas DataFrame."""
    ext = os.path.splitext(raw_path)[1].lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(raw_path, dtype=str, keep_default_na=True)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(raw_path, dtype=str)
        else:
            raise IngestionError(f"Unsupported file extension: {ext}")
    except Exception as e:  # noqa: BLE001 - surface as domain error
        raise IngestionError(f"Failed to parse file: {e}") from e

    if df.empty or len(df.columns) == 0:
        raise IngestionError("File contains no columns/data")

    # Normalize column names: strip whitespace, keep original casing for display
    df.columns = [str(c).strip() for c in df.columns]
    return df


def write_parquet(df: pd.DataFrame, dataset_id: str, upload_dir: str) -> str:
    dataset_dir = os.path.join(upload_dir, dataset_id)
    os.makedirs(dataset_dir, exist_ok=True)
    parquet_path = os.path.join(dataset_dir, "processed.parquet")
    tmp_path = os.path.join(dataset_dir, f"processed.parquet.{uuid.uuid4().hex}.tmp")
    df.to_parquet(tmp_path, index=False)
    os.replace(tmp_path, parquet_path)
    return parquet_path
