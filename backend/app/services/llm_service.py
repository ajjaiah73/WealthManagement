"""Claude-backed agents for the neural half of the neuro-symbolic pipeline.

- LLMIntentExtractor: turns the advisor's free-text request into a structured goal,
  constraints, and a retrieval query (Intent & Fact-Finding Agent).
- LLMSynthesisAdvisor: chooses the product from a symbolically pre-screened
  candidate list and explains why, grounded in retrieved evidence and any
  compliance critique (Advisory Synthesis Agent).
- LLMNarrator: writes the client-facing rationale once compliance has decided.

What the LLM can never do: change allocations or fees (copied from the product
catalogue), pick a product outside the eligible enum (enforced by the JSON
schema and re-checked here), or override the Compliance Agent — the
deterministic/Z3 rule engine runs after synthesis and its verdict is final.

Fail-safe by design: every call returns None on any API error or refusal, and
the orchestrator falls back to the deterministic implementation for that step.
The API key stays server-side; it is never logged or returned to clients.
"""
import json
import logging
from typing import Any, cast

import anthropic
from anthropic.types.beta import BetaOutputConfigParam

from app.domain.advisory import AdvisoryRecommendation
from app.domain.client import ClientProfile
from app.domain.product import Product
from app.domain.retrieval import RetrievedDocument

logger = logging.getLogger(__name__)

PROMPT_VERSION = "2026-10-04.1"


class ClaudeClient:
    """Thin wrapper owning the SDK client and the shared failure policy."""

    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        # base_url and auth_token pinned explicitly so stray ANTHROPIC_BASE_URL /
        # ANTHROPIC_AUTH_TOKEN environment variables can never redirect requests.
        self._client = anthropic.Anthropic(
            api_key=api_key,
            auth_token=None,
            base_url="https://api.anthropic.com",
            timeout=60.0,
            max_retries=1,
        )

    def _create(self, system: str, user: str, max_tokens: int, output_config: dict[str, Any]) -> Any | None:
        try:
            response = self._client.beta.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                # Server-side fallback keeps the agent available if the primary model is overloaded.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                output_config=cast(BetaOutputConfigParam, output_config),
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.AuthenticationError:
            logger.warning("Claude call skipped: invalid ANTHROPIC_API_KEY")
            return None
        except anthropic.APIError as exc:
            logger.warning("Claude call failed, using deterministic fallback: %s", type(exc).__name__)
            return None
        if response.stop_reason == "refusal":
            logger.warning("Claude declined the request, using deterministic fallback")
            return None
        if response.stop_reason == "max_tokens":
            logger.warning("Claude response truncated at max_tokens, using deterministic fallback")
            return None
        return response

    def text(self, system: str, user: str, max_tokens: int = 1024) -> str | None:
        response = self._create(system, user, max_tokens, {"effort": "low"})
        if response is None:
            return None
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        return text or None

    def structured(self, system: str, user: str, schema: dict[str, Any], max_tokens: int = 2048) -> dict | None:
        response = self._create(
            system, user, max_tokens, {"effort": "low", "format": {"type": "json_schema", "schema": schema}}
        )
        if response is None:
            return None
        text = "".join(block.text for block in response.content if block.type == "text")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Claude returned non-JSON structured output, using deterministic fallback")
            return None
        return data if isinstance(data, dict) else None


def _profile_facts(profile: ClientProfile) -> str:
    def money(v: float | None) -> str:
        return f"${v:,.0f}" if v is not None else "not provided"

    return "\n".join([
        f"- Age: {profile.age if profile.age is not None else 'not provided'}",
        f"- Salary: {money(profile.salary)}",
        f"- Super balance: {money(profile.super_balance)}",
        f"- Risk tolerance: {profile.risk_tolerance.value if profile.risk_tolerance else 'not provided'}",
        f"- Target retirement age: {profile.target_retirement_age or 'not provided'}",
        f"- Concessional contributions YTD: {money(profile.concessional_contributions_ytd)}",
        f"- Non-concessional contributions YTD: {money(profile.non_concessional_contributions_ytd)}",
        f"- Transition-to-retirement intent: {profile.ttr_intent}",
        f"- Objectives: {'; '.join(profile.investment_objectives) or 'none recorded'}",
        f"- Goals: {'; '.join(profile.financial_goals) or 'none recorded'}",
        f"- Constraints: {'; '.join(profile.constraints) or 'none recorded'}",
    ])


def _evidence(retrieved: list[RetrievedDocument]) -> str:
    if not retrieved:
        return "(no documents retrieved)"
    return "\n".join(f"[{d.document_id}] {d.document}: {d.snippet}" for d in retrieved)


# --------------------------------------------------------------------------- intent
INTENT_SYSTEM = (
    "You are the Intent & Fact-Finding Agent in an Australian superannuation advisory platform. "
    "Read the adviser's request and the client's fact-find, and extract the advice goal, the explicit "
    "or implied constraints, and a concise search query for retrieving relevant product disclosure "
    "statements and regulation. Use only information present in the input; do not assume missing facts."
)

INTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "goal": {"type": "string", "description": "One sentence: what the client needs advice on."},
        "constraints": {"type": "array", "items": {"type": "string"}},
        "retrieval_query": {"type": "string", "description": "Under 30 words, keyword rich."},
    },
    "required": ["goal", "constraints", "retrieval_query"],
    "additionalProperties": False,
}


class LLMIntentExtractor:
    def __init__(self, client: ClaudeClient) -> None:
        self._client = client
        self.model = client.model

    def extract(self, profile: ClientProfile, request: str) -> dict[str, Any] | None:
        user = f"Adviser request:\n{request}\n\nClient fact-find:\n{_profile_facts(profile)}"
        data = self._client.structured(INTENT_SYSTEM, user, INTENT_SCHEMA)
        if data is None or not str(data.get("goal", "")).strip():
            return None
        return {
            "goal": str(data["goal"]).strip(),
            "constraints": [str(c).strip() for c in data.get("constraints", []) if str(c).strip()],
            "retrieval_query": str(data.get("retrieval_query") or request).strip(),
        }


# ------------------------------------------------------------------------ synthesis
SYNTHESIS_SYSTEM = (
    "You are the Advisory Synthesis Agent in an Australian superannuation advisory platform. Choose the "
    "single most suitable product for the client from the eligible candidate list, using the client's "
    "fact-find, the retrieved regulatory and product evidence, and the platform policy thresholds. "
    "A separate deterministic compliance engine will verify your choice against those thresholds and can "
    "reject it; if compliance critique from a previous attempt is provided, your new choice must resolve "
    "every point raised. Prefer lower fees when suitability is otherwise similar. Ground your reasoning "
    "in the evidence and cite document IDs in square brackets. Do not invent figures."
)

POLICY_THRESHOLDS = (
    "Policy thresholds enforced by the compliance engine:\n"
    "- Concessional contributions cap $30,000 p.a.; non-concessional cap $120,000 p.a.\n"
    "- Transition-to-retirement products require age >= 60 (preservation age).\n"
    "- With 3 or fewer years to target retirement, growth allocation must not exceed 50%.\n"
    "- Clients over 55 should hold at least 25% defensive assets (warning if not).\n"
    "- Total fees above 1.75% p.a. are flagged for review; above 3.00% are rejected."
)


def _synthesis_schema(candidate_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "product_id": {"type": "string", "enum": candidate_ids},
            "reasoning": {"type": "string", "description": "3-5 sentences, citing [DOC-xxx] evidence."},
            "risks": {"type": "array", "items": {"type": "string"}, "description": "2-4 client-specific risks."},
        },
        "required": ["product_id", "reasoning", "risks"],
        "additionalProperties": False,
    }


class LLMSynthesisAdvisor:
    def __init__(self, client: ClaudeClient) -> None:
        self._client = client
        self.model = client.model

    def choose(
        self,
        profile: ClientProfile,
        goal: str | None,
        candidates: list[Product],
        retrieved: list[RetrievedDocument],
        critique_notes: list[str],
    ) -> dict[str, Any] | None:
        if not candidates:
            return None
        catalogue = "\n".join(
            f"- {p.product_id}: {p.product_name} ({p.product_type.value}), option {p.investment_option}, "
            f"growth/defensive {p.growth_defensive_split}, risk {p.risk_level}, "
            f"total fee {p.total_fee_pct:.2f}% p.a."
            for p in candidates
        )
        sections = [
            f"Advice goal: {goal or 'Recommend a suitable superannuation strategy.'}",
            f"Client fact-find:\n{_profile_facts(profile)}",
            f"Eligible candidate products:\n{catalogue}",
            f"Retrieved evidence:\n{_evidence(retrieved)}",
            POLICY_THRESHOLDS,
        ]
        if critique_notes:
            sections.append(
                "Compliance critique of the previous draft (must be resolved):\n"
                + "\n".join(f"- {note}" for note in critique_notes)
            )
        candidate_ids = [p.product_id for p in candidates]
        data = self._client.structured(SYNTHESIS_SYSTEM, "\n\n".join(sections), _synthesis_schema(candidate_ids))
        if data is None or data.get("product_id") not in candidate_ids:
            return None
        return {
            "product_id": data["product_id"],
            "reasoning": str(data.get("reasoning", "")).strip(),
            "risks": [str(r).strip() for r in data.get("risks", []) if str(r).strip()][:4],
        }


# ------------------------------------------------------------------------ narrative
NARRATIVE_SYSTEM = (
    "You are the Advisory Synthesis Agent inside an Australian superannuation "
    "advisory platform. A deterministic engine has already selected the product, "
    "allocation, and fees, and a deterministic compliance engine has verified the "
    "recommendation — you must not change or contradict any of those facts. "
    "Write the client-facing rationale paragraph for the Statement of Advice: "
    "3-5 sentences, plain professional English, grounded strictly in the facts "
    "provided. Do not invent figures, products, or guarantees. Do not give "
    "personal advice beyond the provided recommendation. Output only the "
    "rationale paragraph, no headings or preamble."
)

# Backwards-compatible alias.
SYSTEM_PROMPT = NARRATIVE_SYSTEM


class LLMNarrator:
    """Writes recommendation rationales with a real Claude call."""

    def __init__(self, api_key: str, model: str, client: ClaudeClient | None = None) -> None:
        self.model = model
        self._claude = client or ClaudeClient(api_key=api_key, model=model)

    @property
    def _client(self) -> Any:
        return self._claude._client

    @_client.setter
    def _client(self, value: Any) -> None:
        # Tests swap the SDK client for a stub.
        self._claude._client = value

    def write_rationale(
        self,
        profile: ClientProfile,
        recommendation: AdvisoryRecommendation,
        retrieved: list[RetrievedDocument],
        critique_notes: list[str],
    ) -> str | None:
        facts = [
            f"Client: age {profile.age}, salary ${profile.salary:,.0f},"
            if profile.salary is not None
            else f"Client: age {profile.age},",
            f"super balance ${profile.super_balance:,.0f},"
            if profile.super_balance is not None
            else "",
            f"risk tolerance {profile.risk_tolerance.value if profile.risk_tolerance else 'unknown'},",
            f"target retirement age {profile.target_retirement_age}.",
            f"Goals: {'; '.join(profile.financial_goals) or 'not stated'}.",
            f"Recommended product: {recommendation.strategy_name}"
            f" ({recommendation.product_type}), allocation {recommendation.allocation},"
            f" total fee {recommendation.fee_percentage:.2f}% p.a.",
            f"Source documents: {', '.join(d.document for d in retrieved) or 'none'}.",
        ]
        if critique_notes:
            facts.append(
                "This recommendation replaced an earlier draft after the compliance "
                f"engine raised: {'; '.join(critique_notes)}. Briefly acknowledge the "
                "more suitable positioning without naming the compliance engine."
            )
        return self._claude.text(NARRATIVE_SYSTEM, " ".join(part for part in facts if part))
