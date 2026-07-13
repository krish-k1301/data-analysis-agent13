import logging
import os
from typing import Any

# Must be set before `import litellm`: otherwise litellm's module-level init
# fetches its model-pricing map from raw.githubusercontent.com on every
# process start (~20-25s here, longer or hard-failing on restricted
# networks) before falling back to its bundled copy anyway. This pins it to
# the local copy immediately, since we don't rely on live pricing data.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

import litellm  # noqa: E402

from app.config import settings  # noqa: E402

logger = logging.getLogger(__name__)

litellm.suppress_debug_info = True

AUDIT_EXPLANATION_SYSTEM_PROMPT = (
    "You are a forensic audit analyst. You are given a deterministic, rule-based "
    "finding from an automated audit engine. Your job is to add a richer, "
    "audit-perspective explanation: likely root cause, control implications, and "
    "a recommended next step for the auditor. Use the provided tools if you need "
    "more context about the vendor or dataset before answering. Be concise (3-5 "
    "sentences), factual, and do not contradict the template explanation or "
    "invent numbers not present in the data."
)


class LLMUnavailableError(Exception):
    pass


def get_completion(messages: list[dict], tools: list[dict] | None = None, tool_choice: Any = None):
    """Provider-agnostic LLM call via LiteLLM. Swap provider by changing
    LLM_MODEL (and LLM_API_KEY) in .env — no code changes needed.
    """
    if not settings.LLM_API_KEY:
        raise LLMUnavailableError("LLM_API_KEY is not configured")

    kwargs: dict[str, Any] = dict(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        messages=messages,
        temperature=0.2,
    )
    if tools:
        kwargs["tools"] = tools
    if tool_choice:
        kwargs["tool_choice"] = tool_choice

    try:
        return litellm.completion(**kwargs)
    except Exception as e:  # noqa: BLE001 - any provider failure degrades gracefully
        logger.warning("LLM completion failed: %s", e)
        raise LLMUnavailableError(str(e)) from e
