from app.domain.advisory import AdvisoryRecommendation
from app.domain.client import ClientProfile, RiskTolerance
from app.domain.compliance import ComplianceStatus
from app.services.compliance_service import ComplianceService

DISCLOSURES = [
    "This is general advice only and does not take into account your full personal circumstances.",
    "Refer to the relevant Product Disclosure Statement (PDS) before making a decision.",
]


def _profile(**overrides: object) -> ClientProfile:
    defaults: dict[str, object] = dict(
        client_id="C-TEST", first_name="Test", last_name="User", age=40, salary=100_000,
        super_balance=100_000, risk_tolerance=RiskTolerance.MODERATE, target_retirement_age=65,
        concessional_contributions_ytd=10_000, non_concessional_contributions_ytd=10_000, ttr_intent=False,
    )
    defaults.update(overrides)
    return ClientProfile(**defaults)


def _recommendation(**overrides: object) -> AdvisoryRecommendation:
    defaults: dict[str, object] = dict(
        strategy_name="Test Strategy", product_id="P-TEST", product_type="MySuper", allocation="50/50",
        fee_percentage=0.7, rationale="test", disclosures=list(DISCLOSURES),
    )
    defaults.update(overrides)
    return AdvisoryRecommendation(**defaults)


def test_compliant_recommendation_passes() -> None:
    result = ComplianceService().evaluate("CASE-1", _profile(), _recommendation())
    assert result.status == ComplianceStatus.COMPLIANT
    assert result.rules_failed == 0


def test_concessional_cap_breach_rejects() -> None:
    profile = _profile(concessional_contributions_ytd=35_000)
    result = ComplianceService().evaluate("CASE-1", profile, _recommendation())
    assert result.status == ComplianceStatus.REJECTED
    rule = next(r for r in result.rule_results if r.rule_id == "CONTRIB-001")
    assert rule.passed is False


def test_ttr_below_preservation_age_fails() -> None:
    profile = _profile(age=55, ttr_intent=True)
    result = ComplianceService().evaluate("CASE-1", profile, _recommendation(product_type="TTR"))
    assert result.status == ComplianceStatus.REJECTED
    rule = next(r for r in result.rule_results if r.rule_id == "PRES-001")
    assert rule.passed is False


def test_high_growth_allocation_near_retirement_fails() -> None:
    profile = _profile(age=63, target_retirement_age=65)
    result = ComplianceService().evaluate("CASE-1", profile, _recommendation(allocation="90/10"))
    assert result.status == ComplianceStatus.REJECTED
    rule = next(r for r in result.rule_results if r.rule_id == "ALLOC-001")
    assert rule.passed is False


def test_fee_above_warning_threshold_produces_warning_status() -> None:
    profile = _profile(age=40, target_retirement_age=65)
    result = ComplianceService().evaluate(
        "CASE-1", profile, _recommendation(fee_percentage=2.0, allocation="50/50")
    )
    assert result.status == ComplianceStatus.WARNING
    assert result.warnings >= 1


def test_fee_above_reject_threshold_rejects() -> None:
    result = ComplianceService().evaluate("CASE-1", _profile(), _recommendation(fee_percentage=3.5))
    assert result.status == ComplianceStatus.REJECTED
    rule = next(r for r in result.rule_results if r.rule_id == "FEE-001")
    assert rule.passed is False


def test_fee_warning_is_counted_once() -> None:
    result = ComplianceService().evaluate("CASE-1", _profile(), _recommendation(fee_percentage=1.9))
    rule = next(r for r in result.rule_results if r.rule_id == "FEE-001")
    assert rule.is_warning is True
    assert rule.passed is False
    assert result.status == ComplianceStatus.WARNING
    assert result.rules_passed + result.rules_failed + result.warnings == result.rules_evaluated


def test_missing_mandatory_disclosure_rejects() -> None:
    result = ComplianceService().evaluate("CASE-1", _profile(), _recommendation(disclosures=[]))
    assert result.status == ComplianceStatus.REJECTED
    disclosure_rules = [r for r in result.rule_results if r.category == "Mandatory Disclosures"]
    assert any(not r.passed for r in disclosure_rules)
