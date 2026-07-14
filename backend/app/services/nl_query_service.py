import re
from typing import Any

from app.llm.client import get_completion
from app.services.duckdb_service import QueryValidationError, validate_readonly_sql

NL_TO_SQL_SYSTEM_PROMPT = (
    "You are a SQL generator for DuckDB. You are given a table named `dataset` "
    "with a list of columns and their types, and a plain-English question from "
    "an auditor. Respond with ONLY a single read-only SQL SELECT statement (no "
    "markdown fences, no explanation) that answers the question against the "
    "`dataset` table. Use only the columns listed. Never use INSERT, UPDATE, "
    "DELETE, DROP, ALTER, or any statement other than SELECT/WITH. If the "
    "question cannot be answered with the given columns, respond with a SELECT "
    "that returns an empty result rather than inventing columns."
)


class NLQueryGenerationError(Exception):
    pass


def _format_schema(profile_json: dict[str, Any]) -> str:
    columns = profile_json.get("columns", {})
    lines = []
    for name, col in columns.items():
        col_type = col.get("type", "unknown")
        samples = col.get("sample_values", [])[:3]
        lines.append(f"- {name} ({col_type}), examples: {samples}")
    return "\n".join(lines)


def _strip_sql_fences(text: str) -> str:
    text = text.strip()
    match = re.match(r"^```(?:sql)?\s*(.*?)\s*```$", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def generate_sql_from_question(question: str, profile_json: dict[str, Any]) -> str:
    schema_description = _format_schema(profile_json)
    messages = [
        {"role": "system", "content": NL_TO_SQL_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Table `dataset` columns:\n{schema_description}\n\n"
                f"Question: {question}"
            ),
        },
    ]

    response = get_completion(messages)
    raw_sql = response.choices[0].message.content or ""
    sql = _strip_sql_fences(raw_sql)

    try:
        validate_readonly_sql(sql)
    except QueryValidationError as e:
        raise NLQueryGenerationError(f"Generated SQL failed validation: {e}") from e

    return sql
