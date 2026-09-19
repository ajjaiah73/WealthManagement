from typing import Literal
from pydantic import BaseModel, Field, model_validator
class ClientProfile(BaseModel):
    client_id: str
    age: int = Field(ge=18, le=100)
    annual_income: float = Field(ge=0)
    liquid_assets: float = Field(ge=0)
    risk_tolerance: Literal["conservative","moderate","aggressive"]
    investment_horizon_years: int = Field(ge=1, le=50)
    max_fee_pct: float = Field(default=2.0, ge=0, le=10)
    restricted_products: list[str] = []
class AdviceRequest(BaseModel):
    client: ClientProfile
    goal: str = Field(min_length=5)
    question: str = Field(min_length=5)
class Allocation(BaseModel):
    # equity_pct: float = Field(ge=0, le=100)
    # bond_pct: float = Field(ge=0, le=100)
    # cash_pct: float = Field(ge=0, le=100)
    # Added By Ajjaiah M E on 20th Sep 2026
    equity_pct: float = Field(ge=0, le=100)
    bond_pct: float = Field(ge=0, le=100)
    cash_pct: float = Field(ge=0, le=100)
    @model_validator(mode="after")
    def total_100(self):
        if abs(self.equity_pct+self.bond_pct+self.cash_pct-100)>0.01:
            raise ValueError("Allocation must total 100")
        return self
class ProductRecommendation(BaseModel):
    product_id: str
    name: str
    category: str
    allocation_pct: float = Field(ge=0, le=100)
    fee_pct: float = Field(ge=0, le=10)
    rationale: str
    source_ids: list[str]
class ComplianceFinding(BaseModel):
    rule_id: str
    severity: Literal["info","warning","error"]
    passed: bool
    message: str
class AdviceResponse(BaseModel):
    audit_id: str
    statement_of_advice: str
    allocation: Allocation
    recommendations: list[ProductRecommendation]
    citations: list[dict]
    compliance_findings: list[ComplianceFinding]
    compliant: bool
    reflection_count: int
    audit_notes: list[str]
