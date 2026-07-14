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


def get_completion(
    messages: list[dict],
    tools: list[dict] | None = None,
    tool_choice: Any = None,
    model: str | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
    timeout: int | None = None,
):
    """Provider-agnostic LLM call via LiteLLM. Defaults to the query model
    (LLM_MODEL/LLM_API_KEY in .env); pass model/api_base explicitly to target
    a different backend (e.g. the local Ollama model used for findings —
    see FINDINGS_LLM_MODEL). No code changes needed to swap providers.
    """
    model = model or settings.LLM_MODEL
    api_base = api_base or None
    is_local = model.startswith("ollama")

    if api_key is None:
        api_key = None if is_local else settings.LLM_API_KEY
    if not is_local and not api_key:
        raise LLMUnavailableError(f"No API key configured for model '{model}'")

    kwargs: dict[str, Any] = dict(
        model=model,
        messages=messages,
        temperature=0.2,
        timeout=timeout or settings.LLM_TIMEOUT_SECONDS,
    )
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base
    if tools:
        kwargs["tools"] = tools
    if tool_choice:
        kwargs["tool_choice"] = tool_choice

    try:
        return litellm.completion(**kwargs)
    except Exception as e:  # noqa: BLE001 - any provider failure degrades gracefully
        logger.warning("LLM completion failed (model=%s): %s", model, e)
        raise LLMUnavailableError(str(e)) from e
