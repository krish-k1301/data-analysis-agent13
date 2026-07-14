import pandas as pd
import pytest

from app.services.duckdb_service import QueryValidationError, query_parquet


@pytest.fixture()
def sample_parquet(tmp_path):
    df = pd.DataFrame({"vendor": ["A", "B", "A"], "amount": [10.0, 20.0, 30.0]})
    path = tmp_path / "data.parquet"
    df.to_parquet(path, index=False)
    return str(path)


def test_valid_select_query(sample_parquet):
    columns, rows = query_parquet(
        sample_parquet, "SELECT vendor, SUM(amount) as total FROM dataset GROUP BY vendor ORDER BY vendor"
    )
    assert columns == ["vendor", "total"]
    assert rows == [{"vendor": "A", "total": 40.0}, {"vendor": "B", "total": 20.0}]


def test_valid_query_with_cte(sample_parquet):
    columns, rows = query_parquet(
        sample_parquet, "WITH t AS (SELECT * FROM dataset) SELECT COUNT(*) as n FROM t"
    )
    assert rows == [{"n": 3}]


def test_path_with_single_quote_is_escaped_safely(tmp_path):
    df = pd.DataFrame({"amount": [1.0, 2.0]})
    tricky_dir = tmp_path / "o'brien"
    tricky_dir.mkdir()
    path = tricky_dir / "data.parquet"
    df.to_parquet(path, index=False)

    columns, rows = query_parquet(str(path), "SELECT COUNT(*) as n FROM dataset")
    assert rows == [{"n": 2}]


def test_rejects_multiple_statements(sample_parquet):
    with pytest.raises(QueryValidationError):
        query_parquet(sample_parquet, "SELECT * FROM dataset; DROP TABLE dataset;")


def test_rejects_non_select(sample_parquet):
    with pytest.raises(QueryValidationError):
        query_parquet(sample_parquet, "DELETE FROM dataset")


def test_rejects_ddl_keyword_embedded(sample_parquet):
    with pytest.raises(QueryValidationError):
        query_parquet(sample_parquet, "SELECT * FROM dataset WHERE 1=1 create table x(y int)")


def test_rejects_empty_query(sample_parquet):
    with pytest.raises(QueryValidationError):
        query_parquet(sample_parquet, "   ")


def test_syntax_error_raises_non_validation_error(sample_parquet):
    with pytest.raises(Exception) as exc_info:
        query_parquet(sample_parquet, "SELECT FROM WHERE malformed")
    assert not isinstance(exc_info.value, QueryValidationError)


def test_limit_applied_when_not_specified(sample_parquet):
    columns, rows = query_parquet(sample_parquet, "SELECT * FROM dataset", limit=1)
    assert len(rows) == 1


def test_limit_not_duplicated_when_already_present(sample_parquet):
    columns, rows = query_parquet(sample_parquet, "SELECT * FROM dataset LIMIT 2", limit=1)
    assert len(rows) == 2  # user's own LIMIT wins, ours isn't appended on top
