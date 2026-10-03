from app.domain.document import DocumentRecord, DocumentType
from app.mock_data.products import SEED_PRODUCTS

_PDS_DOCUMENTS: list[DocumentRecord] = [
    DocumentRecord(
        document_id=product.source_document_id or f"DOC-{product.product_id}",
        title=f"{product.product_name} - Product Disclosure Statement",
        document_type=DocumentType.PDS,
        source=product.product_name.split(" ")[0],
        page_count=48,
        published_date="2025-07-01",
        url=None,
        full_text_excerpt=(
            f"{product.product_name} ({product.product_type.value}) charges a management fee of "
            f"{product.management_fee_pct:.2f}% and an administration fee of "
            f"{product.administration_fee_pct:.2f}%. "
            f"The standard investment option is {product.investment_option} with a "
            f"{product.growth_defensive_split} growth/defensive split, classified {product.risk_level} risk."
        ),
    )
    for product in SEED_PRODUCTS
]

_REGULATORY_DOCUMENTS: list[DocumentRecord] = [
    DocumentRecord(
        document_id="DOC-014",
        title="SIS Act 1993 - Section 292: Concessional Contributions Cap",
        document_type=DocumentType.LEGISLATION,
        source="Federal Register of Legislation",
        page_count=6,
        published_date="2024-07-01",
        full_text_excerpt=(
            "The concessional contributions cap for the 2024-25 and 2025-26 financial years is $30,000 per "
            "annum. Contributions in excess of the cap are subject to additional tax under Division 293."
        ),
    ),
    DocumentRecord(
        document_id="DOC-015",
        title="SIS Act 1993 - Section 292: Non-Concessional Contributions Cap",
        document_type=DocumentType.LEGISLATION,
        source="Federal Register of Legislation",
        page_count=5,
        published_date="2024-07-01",
        full_text_excerpt=(
            "The non-concessional contributions cap for the 2024-25 and 2025-26 financial years is $120,000 "
            "per annum, subject to the bring-forward rule for eligible members under age 75."
        ),
    ),
    DocumentRecord(
        document_id="DOC-016",
        title="SIS Regulations 1994 - Preservation Age and Transition to Retirement",
        document_type=DocumentType.LEGISLATION,
        source="Federal Register of Legislation",
        page_count=9,
        published_date="2023-11-15",
        full_text_excerpt=(
            "A member's preservation age is 60 for all persons born after 30 June 1964. Transition to "
            "Retirement (TTR) income streams are only available to members who have reached preservation age."
        ),
    ),
    DocumentRecord(
        document_id="DOC-017",
        title="APRA Guidance - Asset Allocation Appropriateness for Pre-Retirees",
        document_type=DocumentType.REGULATORY_GUIDANCE,
        source="APRA",
        page_count=14,
        published_date="2024-03-20",
        full_text_excerpt=(
            "For members aged over 55, APRA guidance recommends a defensive allocation of at least 25% "
            "unless the member has explicitly acknowledged and accepted a higher-risk profile in writing."
        ),
    ),
    DocumentRecord(
        document_id="DOC-018",
        title="APRA Superannuation Fee Benchmark Report",
        document_type=DocumentType.REGULATORY_GUIDANCE,
        source="APRA",
        page_count=22,
        published_date="2025-02-10",
        full_text_excerpt=(
            "Total fund fees (management plus administration) above 1.75% per annum are flagged for advisor "
            "review as exceeding typical market benchmarks; fees above 3.00% require documented justification."
        ),
    ),
    DocumentRecord(
        document_id="DOC-019",
        title="Corporations Act 2001 - Advice Disclosure Obligations",
        document_type=DocumentType.LEGISLATION,
        source="Federal Register of Legislation",
        page_count=11,
        published_date="2023-01-01",
        full_text_excerpt=(
            "Where advice is provided on a general advice basis, the provider must disclose that the advice "
            "does not take into account the client's personal circumstances and direct them to the relevant "
            "Product Disclosure Statement before acting."
        ),
    ),
    DocumentRecord(
        document_id="DOC-020",
        title="ASIC Fact Sheet - Understanding Division 293 Tax",
        document_type=DocumentType.FACT_SHEET,
        source="ASIC MoneySmart",
        page_count=4,
        published_date="2024-09-05",
        full_text_excerpt=(
            "Division 293 tax is an additional 15% tax on concessional contributions for individuals with "
            "income plus relevant contributions above $250,000 in a financial year."
        ),
    ),
]

SEED_DOCUMENTS: list[DocumentRecord] = _PDS_DOCUMENTS + _REGULATORY_DOCUMENTS
