import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Must happen before any `app.*` import: app.config.settings is a
# module-level singleton read from env vars / .env at import time.
_TEST_DIR = tempfile.mkdtemp(prefix="audit_agent_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DIR}/test.db"
os.environ["UPLOAD_DIR"] = f"{_TEST_DIR}/uploads"
os.environ["LLM_API_KEY"] = ""  # tests must never depend on / leak a real key
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

SAMPLE_CSV = BACKEND_DIR / "sample_data" / "sample_payments.csv"


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
    _clear_db()


def _clear_db():
    from app.database import SessionLocal
    from app.models import Dataset, DatasetProfile, Finding, ReviewAction, SchemaMapping

    db = SessionLocal()
    try:
        db.query(ReviewAction).delete()
        db.query(Finding).delete()
        db.query(SchemaMapping).delete()
        db.query(DatasetProfile).delete()
        db.query(Dataset).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def clean_amount_df() -> pd.DataFrame:
    """A small, well-formed DataFrame with all canonical columns mapped —
    the 'no findings' baseline for per-rule negative tests.
    """
    dates = pd.date_range("2024-01-02", periods=20, freq="B")  # business days only
    return pd.DataFrame(
        {
            "invoice_no": [f"INV-{1000 + i}" for i in range(20)],
            "vendor": [f"Vendor {i % 5}" for i in range(20)],
            "amount": [1234.56 + i for i in range(20)],
            "date": dates,
            "entry_date": dates,
            "timestamp": [d + pd.Timedelta(hours=10) for d in dates],
        }
    )


@pytest.fixture()
def db_ready():
    """For tests that invoke the LangGraph/service layer directly (not via
    TestClient) but still need migrated tables for persist_node to write to.
    """
    from app.main import run_migrations

    run_migrations()
    yield
    _clear_db()


@pytest.fixture()
def rule_config() -> dict:
    return {
        "materiality_threshold": 50000,
        "MATERIALITY_THRESHOLD": 50000,
        "dormant_vendor_days": 180,
        "new_vendor_window_days": 30,
        "new_vendor_high_value": 10000,
        "vendor_concentration_pct": 40,
        "benford_p_value": 0.05,
        "outlier_zscore_threshold": 3.0,
    }
