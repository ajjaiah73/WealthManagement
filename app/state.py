from typing import TypedDict, Any
from .models import AdviceRequest
class AdvisoryState(TypedDict, total=False):
    request: AdviceRequest
    query: str
    contexts: list[dict[str, Any]]
    draft: dict[str, Any]
    compliance_findings: list[dict[str, Any]]
    compliant: bool
    reflection_count: int
    critique: str
    final: dict[str, Any]
