from types import SimpleNamespace
from typing import Any

import anthropic
import httpx

from app.container import container
from app.domain.advisory import AdvisoryRecommendation
from app.services.llm_service import LLMNarrator


def _inputs() -> tuple[Any, AdvisoryRecommendation]:
    profile = container.client_repository.get("C-0001")
    assert profile is not None
    recommendation = AdvisoryRecommendation(
        strategy_name="Test Strategy",
        product_id="P-001",
        product_type="MySuper",
        allocation="70/30",
        fee_percentage=0.85,
        rationale="template",
        assumptions=[],
        risks=[],
        source_documents=[],
        disclosures=[],
    )
    return profile, recommendation


def _narrator(create: Any) -> LLMNarrator:
    narrator = LLMNarrator(api_key="test-key", model="test-model")
    narrator._client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))
    return narrator


def test_api_error_falls_back_to_template() -> None:
    def fail(**_: Any) -> None:
        raise anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))

    profile, rec = _inputs()
    assert _narrator(fail).write_rationale(profile, rec, [], []) is None


def test_refusal_falls_back_to_template() -> None:
    def refuse(**_: Any) -> Any:
        return SimpleNamespace(stop_reason="refusal", content=[])

    profile, rec = _inputs()
    assert _narrator(refuse).write_rationale(profile, rec, [], []) is None


def test_successful_call_returns_text() -> None:
    def ok(**_: Any) -> Any:
        return SimpleNamespace(
            stop_reason="end_turn", content=[SimpleNamespace(type="text", text="  Grounded rationale. ")]
        )

    profile, rec = _inputs()
    assert _narrator(ok).write_rationale(profile, rec, [], []) == "Grounded rationale."
