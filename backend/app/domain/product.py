from enum import Enum

from pydantic import BaseModel, Field


class ProductType(str, Enum):
    MY_SUPER = "MySuper"
    CHOICE = "Choice"
    SMSF = "SMSF"
    TTR = "TTR"
    DEFINED_BENEFIT = "Defined Benefit"


class Product(BaseModel):
    product_id: str
    product_name: str
    product_type: ProductType
    management_fee_pct: float = Field(ge=0)
    administration_fee_pct: float = Field(ge=0)
    investment_option: str
    growth_defensive_split: str  # e.g. "80/20" (growth/defensive)
    risk_level: str
    source_document_id: str | None = None

    @property
    def total_fee_pct(self) -> float:
        return round(self.management_fee_pct + self.administration_fee_pct, 4)
