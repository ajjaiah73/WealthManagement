"""Deterministic Neuro-Symbolic Compliance Engine.

This is the REAL implementation, not a mock — every rule here is either a
plain deterministic comparison or an SMT (Z3) satisfiability check. LLM output
is never trusted for these checks; the orchestrator only ever asks this
service to accept or reject a proposed AdvisoryRecommendation.

Cap/threshold figures are representative for demonstration purposes and
should be reviewed against current ATO/APRA guidance before production use.
"""
from datetime import UTC, datetime

import z3

from app.domain.advisory import AdvisoryRecommendation
from app.domain.client import ClientProfile
from app.domain.compliance import ComplianceResult, ComplianceRuleResult, ComplianceStatus
from app.domain.product import ProductType

ENGINE_VERSION = "neuro-symbolic-compliance-v0.1.0"

CONCESSIONAL_CAP = 30_000.0
NON_CONCESSIONAL_CAP = 120_000.0
PRESERVATION_AGE = 60
FEE_WARNING_THRESHOLD_PCT = 1.75
FEE_REJECT_THRESHOLD_PCT = 3.0
MIN_DEFENSIVE_PCT_OVER_55 = 25.0
MANDATORY_DISCLOSURE_KEYWORDS = ("general advice", "product disclosure statement")


def _parse_allocation(allocation: str) -> tuple[float, float]:
    """Parses "80/20" -> (growth=80.0, defensive=20.0); (0, 0) if unparsable."""
    try:
        growth_str, defensive_str = allocation.replace("%", "").split("/")
        return float(growth_str.strip()), float(defensive_str.strip())
    except (ValueError, AttributeError):
        return 0.0, 0.0


def _cap_satisfiable(amount: float, cap: float) -> bool:
    """SMT-based cap check — establishes the neuro-symbolic pattern for hard
    numeric constraints (extend with combined-cap / Division 293 constraints
    in a later phase)."""
    x = z3.Real("contribution_amount")
    solver = z3.Solver()
    solver.add(x == amount)
    solver.add(x <= z3.RealVal(cap))
    return solver.check() == z3.sat


class ComplianceService:
    def evaluate(
        self, case_id: str, profile: ClientProfile, recommendation: AdvisoryRecommendation
    ) -> ComplianceResult:
        results: list[ComplianceRuleResult] = []

        concessional_ok = _cap_satisfiable(profile.concessional_contributions_ytd, CONCESSIONAL_CAP)
        results.append(ComplianceRuleResult(
            rule_id="CONTRIB-001",
            category="Contribution Limits",
            passed=concessional_ok,
            detail=(
                f"Concessional contributions YTD (${profile.concessional_contributions_ytd:,.2f}) "
                f"{'within' if concessional_ok else 'exceed'} the ${CONCESSIONAL_CAP:,.0f} cap."
            ),
            evidence="SIS Act 1993 s.292 - Concessional Contributions Cap",
        ))

        non_concessional_ok = _cap_satisfiable(profile.non_concessional_contributions_ytd, NON_CONCESSIONAL_CAP)
        results.append(ComplianceRuleResult(
            rule_id="CONTRIB-002",
            category="Contribution Limits",
            passed=non_concessional_ok,
            detail=(
                f"Non-concessional contributions YTD (${profile.non_concessional_contributions_ytd:,.2f}) "
                f"{'within' if non_concessional_ok else 'exceed'} the ${NON_CONCESSIONAL_CAP:,.0f} cap."
            ),
            evidence="SIS Act 1993 s.292 - Non-Concessional Contributions Cap",
        ))

        if recommendation.product_type == ProductType.TTR.value:
            ttr_ok = profile.age is not None and profile.age >= PRESERVATION_AGE
            results.append(ComplianceRuleResult(
                rule_id="PRES-001",
                category="Preservation Age",
                passed=ttr_ok,
                detail=(
                    f"Client age {profile.age} "
                    f"{'meets' if ttr_ok else 'is below'} the TTR preservation age of {PRESERVATION_AGE}."
                ),
                evidence="SIS Regulations 1994 - Preservation Age / TTR eligibility",
            ))

        growth_pct, defensive_pct = _parse_allocation(recommendation.allocation)
        years_to_retire = None
        if profile.age is not None and profile.target_retirement_age is not None:
            years_to_retire = profile.target_retirement_age - profile.age

        allocation_ok = not (years_to_retire is not None and years_to_retire <= 3 and growth_pct > 50)
        results.append(ComplianceRuleResult(
            rule_id="ALLOC-001",
            category="Allocation Constraints",
            passed=allocation_ok,
            detail=(
                "Growth allocation is consistent with the client's time horizon."
                if allocation_ok else
                f"High-growth allocation ({recommendation.allocation}) is inappropriate with only "
                f"{years_to_retire} years to target retirement."
            ),
            evidence="APRA Guidance - Asset Allocation Appropriateness",
        ))

        if profile.age is not None and profile.age > 55:
            defensive_ok = defensive_pct >= MIN_DEFENSIVE_PCT_OVER_55
            results.append(ComplianceRuleResult(
                rule_id="ALLOC-002",
                category="Allocation Constraints",
                passed=defensive_ok,
                is_warning=not defensive_ok,
                detail=(
                    f"Defensive component ({defensive_pct:.0f}%) "
                    f"{'meets' if defensive_ok else 'is below'} the {MIN_DEFENSIVE_PCT_OVER_55:.0f}% "
                    f"floor recommended for clients over 55."
                ),
                evidence="APRA Guidance - Defensive Allocation for Pre-Retirees",
            ))

        fee_fail = recommendation.fee_percentage > FEE_REJECT_THRESHOLD_PCT
        fee_warn = not fee_fail and recommendation.fee_percentage > FEE_WARNING_THRESHOLD_PCT
        threshold_hit = FEE_REJECT_THRESHOLD_PCT if fee_fail else FEE_WARNING_THRESHOLD_PCT
        results.append(ComplianceRuleResult(
            rule_id="FEE-001",
            category="Fee Thresholds",
            passed=not fee_fail and not fee_warn,
            is_warning=fee_warn,
            detail=(
                f"Proposed fee ({recommendation.fee_percentage:.2f}%) "
                + ("exceeds the hard reject threshold of " if fee_fail
                   else "exceeds the warning threshold of " if fee_warn
                   else "is within the threshold of ")
                + f"{threshold_hit:.2f}%."
            ),
            evidence="APRA Fee Benchmark Guidance",
        ))

        disclosure_text = " ".join(recommendation.disclosures).lower()
        for keyword in MANDATORY_DISCLOSURE_KEYWORDS:
            present = keyword in disclosure_text
            results.append(ComplianceRuleResult(
                rule_id=f"DISC-{keyword.split()[0].upper()}",
                category="Mandatory Disclosures",
                passed=present,
                detail=f"Required disclosure referencing '{keyword}' {'is present' if present else 'is MISSING'}.",
                evidence="Corporations Act 2001 - Advice Disclosure Obligations",
            ))

        rules_failed = sum(1 for r in results if not r.passed and not r.is_warning)
        warnings = sum(1 for r in results if r.is_warning)
        rules_passed = sum(1 for r in results if r.passed)

        if rules_failed > 0:
            status = ComplianceStatus.REJECTED
        elif warnings > 0:
            status = ComplianceStatus.WARNING
        else:
            status = ComplianceStatus.COMPLIANT

        return ComplianceResult(
            case_id=case_id,
            status=status,
            rules_evaluated=len(results),
            rules_passed=rules_passed,
            rules_failed=rules_failed,
            warnings=warnings,
            rule_results=results,
            mandatory_disclosures=list(MANDATORY_DISCLOSURE_KEYWORDS),
            engine_version=ENGINE_VERSION,
            validated_at=datetime.now(UTC),
        )
