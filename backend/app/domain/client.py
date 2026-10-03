from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskTolerance(str, Enum):
    CONSERVATIVE = "Conservative"
    MODERATE = "Moderate"
    GROWTH = "Growth"
    HIGH_GROWTH = "High Growth"


class FieldStatus(str, Enum):
    PRESENT = "present"
    MISSING = "missing"


class FactFindField(BaseModel):
    field: str
    value: Any | None = None
    status: FieldStatus

    @classmethod
    def of(cls, field: str, value: Any) -> "FactFindField":
        is_missing = value is None or (isinstance(value, (list, str)) and len(value) == 0)
        return cls(field=field, value=None if is_missing else value,
                    status=FieldStatus.MISSING if is_missing else FieldStatus.PRESENT)


class FactFind(BaseModel):
    client_id: str
    fields: list[FactFindField]

    @property
    def completion_percentage(self) -> float:
        if not self.fields:
            return 0.0
        present = sum(1 for f in self.fields if f.status == FieldStatus.PRESENT)
        return round(present / len(self.fields) * 100, 1)

    @property
    def missing_fields(self) -> list[str]:
        return [f.field for f in self.fields if f.status == FieldStatus.MISSING]


class ClientProfile(BaseModel):
    client_id: str
    first_name: str
    last_name: str
    age: int | None = Field(default=None, ge=18, le=100)
    salary: float | None = Field(default=None, ge=0)
    super_balance: float | None = Field(default=None, ge=0)
    risk_tolerance: RiskTolerance | None = None
    target_retirement_age: int | None = Field(default=None, ge=45, le=75)
    contribution_history: list[str] = Field(default_factory=list)
    concessional_contributions_ytd: float = Field(default=0.0, ge=0)
    non_concessional_contributions_ytd: float = Field(default=0.0, ge=0)
    ttr_intent: bool | None = None
    investment_objectives: list[str] = Field(default_factory=list)
    financial_goals: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    advisory_status: str = "Not Started"
    compliance_status: str | None = None
    last_review_date: date | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


# Fields the Intent & Fact-Finding Agent must extract. Missing values must be
# surfaced explicitly (never silently assumed) — see FactFindField.of above.
REQUIRED_FACT_FIND_FIELDS = [
    "age",
    "salary",
    "super_balance",
    "risk_tolerance",
    "target_retirement_age",
    "contribution_history",
    "concessional_contributions_ytd",
    "non_concessional_contributions_ytd",
    "ttr_intent",
    "investment_objectives",
    "financial_goals",
    "constraints",
]


def build_fact_find(profile: ClientProfile) -> FactFind:
    fields = [FactFindField.of(name, getattr(profile, name)) for name in REQUIRED_FACT_FIND_FIELDS]
    return FactFind(client_id=profile.client_id, fields=fields)
