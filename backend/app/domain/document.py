from enum import Enum

from pydantic import BaseModel


class DocumentType(str, Enum):
    PDS = "PDS"
    REGULATORY_GUIDANCE = "Regulatory Guidance"
    LEGISLATION = "Legislation"
    FACT_SHEET = "Fact Sheet"


class DocumentRecord(BaseModel):
    document_id: str
    title: str
    document_type: DocumentType
    source: str
    page_count: int | None = None
    published_date: str | None = None
    url: str | None = None
    full_text_excerpt: str
