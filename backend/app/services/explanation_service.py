import json
import logging
from typing import Any

from app.llm.client import AUDIT_EXPLANATION_SYSTEM_PROMPT, LLMUnavailableError, get_completion
from app.llm.tools import MAX_TOOL_ITERATIONS, TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

MAX_ENRICHED_FINDINGS = 50


def _finding_summary(finding: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in finding.items() if k != "flagged_rows"} | {
        "sample_flagged_rows": finding.get("flagged_rows", [])[:3]
    }


def enrich_finding(finding: dict[str, Any], context: dict[str, Any]) -> str | None:
    """Ask the LLM for a richer, audit-perspective explanation of a single
    finding, with tool-calling access to the dataset. Returns None (graceful
    fallback to the deterministic template) if the LLM is unavailable or fails.
    """
    messages = [
        {"role": "system", "content": AUDIT_EXPLANATION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Template explanation:\n{finding['audit_explanation']}\n\n"
                f"Finding data:\n{json.dumps(_finding_summary(finding), default=str)}\n\n"
                f"Provide a richer audit-perspective explanation."
            ),
        },
    ]

    try:
        for _ in range(MAX_TOOL_ITERATIONS):
            response = get_completion(messages, tools=TOOL_DEFINITIONS)
            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)
            if not tool_calls:
                return message.content
            messages.append(message.model_dump())
            for call in tool_calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = execute_tool(call.function.name, args, context)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, default=str),
                    }
                )
        # Iteration cap reached: force a final answer without further tool calls
        response = get_completion(messages)
        return response.choices[0].message.content
    except LLMUnavailableError:
        return None
    except Exception as e:  # noqa: BLE001 - any provider/tooling failure degrades gracefully
        logger.warning("LLM enrichment failed for rule %s: %s", finding.get("rule_id"), e)
        return None


def enrich_findings(findings: list[dict[str, Any]], context: dict[str, Any]) -> list[dict[str, Any]]:
    """Enrich up to MAX_ENRICHED_FINDINGS findings with LLM explanations.
    Findings beyond the cap keep llm_enriched_explanation=None (template only)
    to bound LLM cost/latency on large result sets.
    """
    for i, finding in enumerate(findings):
        if i >= MAX_ENRICHED_FINDINGS:
            finding["llm_enriched_explanation"] = None
            continue
        finding["llm_enriched_explanation"] = enrich_finding(finding, context)
    return findings


def generate_dataset_summary(findings: list[dict[str, Any]], statistics: dict[str, Any], row_count: int) -> str:
    """Deterministic, template-based executive summary of a dataset's audit
    run. Does not depend on the LLM so it is always available.
    """
    if not findings:
        return f"No findings were raised across {row_count} rows for the enabled audit rules."

    by_severity: dict[str, int] = {}
    by_rule: dict[str, int] = {}
    for f in findings:
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
        by_rule[f["rule_name"]] = by_rule.get(f["rule_name"], 0) + 1

    top_rules = sorted(by_rule.items(), key=lambda kv: kv[1], reverse=True)[:3]
    top_rules_str = ", ".join(f"{name} ({count})" for name, count in top_rules)

    severity_str = ", ".join(
        f"{by_severity[s]} {s}" for s in ("HIGH", "MEDIUM", "LOW") if s in by_severity
    )

    return (
        f"Analyzed {row_count} rows and raised {len(findings)} finding(s): {severity_str}. "
        f"Most frequent rule triggers: {top_rules_str}."
    )
