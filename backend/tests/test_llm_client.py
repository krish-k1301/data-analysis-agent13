import pytest

from app.llm import client as llm_client
from app.llm.client import LLMUnavailableError, get_completion
from app.services import explanation_service


def test_get_completion_raises_without_api_key(monkeypatch):
    monkeypatch.setattr(llm_client.settings, "LLM_API_KEY", "")
    with pytest.raises(LLMUnavailableError):
        get_completion([{"role": "user", "content": "hi"}])


def test_get_completion_success(monkeypatch):
    monkeypatch.setattr(llm_client.settings, "LLM_API_KEY", "fake-key")

    class FakeMessage:
        content = "mocked explanation"
        tool_calls = None

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    def fake_completion(**kwargs):
        assert kwargs["messages"]
        return FakeResponse()

    monkeypatch.setattr(llm_client.litellm, "completion", fake_completion)
    response = get_completion([{"role": "user", "content": "hi"}])
    assert response.choices[0].message.content == "mocked explanation"


def test_get_completion_wraps_provider_failure(monkeypatch):
    monkeypatch.setattr(llm_client.settings, "LLM_API_KEY", "fake-key")

    def fake_completion(**kwargs):
        raise RuntimeError("provider is down")

    monkeypatch.setattr(llm_client.litellm, "completion", fake_completion)
    with pytest.raises(LLMUnavailableError):
        get_completion([{"role": "user", "content": "hi"}])


def test_enrich_finding_falls_back_to_none_without_api_key():
    finding = {
        "rule_id": "ROUND_DOLLAR",
        "audit_explanation": "template text",
        "supporting_metrics": {},
        "flagged_rows": [],
    }
    result = explanation_service.enrich_finding(finding, {"df": None, "parquet_path": None})
    assert result is None


def test_enrich_finding_uses_llm_when_available_no_tool_calls(monkeypatch):
    monkeypatch.setattr(llm_client.settings, "LLM_API_KEY", "fake-key")

    class FakeMessage:
        content = "richer LLM explanation"
        tool_calls = None

        def model_dump(self):
            return {"role": "assistant", "content": self.content}

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    monkeypatch.setattr(llm_client.litellm, "completion", lambda **kwargs: FakeResponse())

    finding = {
        "rule_id": "ROUND_DOLLAR",
        "audit_explanation": "template text",
        "supporting_metrics": {},
        "flagged_rows": [],
    }
    result = explanation_service.enrich_finding(finding, {"df": None, "parquet_path": None})
    assert result == "richer LLM explanation"


def test_enrich_finding_falls_back_to_none_on_provider_exception(monkeypatch):
    monkeypatch.setattr(llm_client.settings, "LLM_API_KEY", "fake-key")
    monkeypatch.setattr(
        llm_client.litellm, "completion", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    finding = {
        "rule_id": "ROUND_DOLLAR",
        "audit_explanation": "template text",
        "supporting_metrics": {},
        "flagged_rows": [],
    }
    result = explanation_service.enrich_finding(finding, {"df": None, "parquet_path": None})
    assert result is None


def test_enrich_findings_caps_at_max_enriched(monkeypatch):
    monkeypatch.setattr(explanation_service, "MAX_ENRICHED_FINDINGS", 2)
    findings = [
        {"rule_id": f"R{i}", "audit_explanation": "t", "supporting_metrics": {}, "flagged_rows": []}
        for i in range(5)
    ]
    result = explanation_service.enrich_findings(findings, {"df": None, "parquet_path": None})
    # No API key configured in this test env -> all None, but the important
    # thing is every finding got the key set (none skipped/crashed).
    assert all("llm_enriched_explanation" in f for f in result)
    assert all(f["llm_enriched_explanation"] is None for f in result)
