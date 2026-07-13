import duckdb

FORBIDDEN_KEYWORDS = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "attach",
    "copy",
    "pragma",
    "call",
    "install",
    "load",
    "export",
    "import",
)


class QueryValidationError(Exception):
    pass


def validate_readonly_sql(sql: str) -> None:
    normalized = sql.strip().lower()
    if not normalized:
        raise QueryValidationError("Empty query")
    if ";" in normalized.rstrip(";"):
        raise QueryValidationError("Multiple statements are not allowed")
    if not (normalized.startswith("select") or normalized.startswith("with")):
        raise QueryValidationError("Only SELECT queries are allowed")
    for kw in FORBIDDEN_KEYWORDS:
        if f" {kw} " in f" {normalized} " or normalized.startswith(kw):
            raise QueryValidationError(f"Keyword '{kw}' is not allowed in read-only queries")


def query_parquet(parquet_path: str, sql: str, limit: int | None = None) -> tuple[list[str], list[dict]]:
    """Run a read-only SQL query against a parquet file exposed as table
    'dataset'. Uses an ephemeral in-memory DuckDB connection per call to
    avoid concurrent file-lock contention with the background pipeline.
    """
    validate_readonly_sql(sql)

    con = duckdb.connect(":memory:", read_only=False)
    try:
        # DuckDB doesn't support `?` parameter binding inside CREATE VIEW
        # (view definitions must be static SQL, not a prepared statement) —
        # only in plain SELECTs. parquet_path is server-generated (never
        # user input), so quote-escaping and interpolating is safe here.
        escaped_path = parquet_path.replace("'", "''")
        con.execute(f"CREATE VIEW dataset AS SELECT * FROM read_parquet('{escaped_path}')")
        final_sql = sql.rstrip(";")
        if limit is not None and "limit" not in final_sql.lower():
            final_sql = f"{final_sql} LIMIT {int(limit)}"
        result = con.execute(final_sql)
        columns = [desc[0] for desc in result.description]
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return columns, rows
    finally:
        con.close()
