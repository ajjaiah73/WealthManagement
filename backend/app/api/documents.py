from fastapi import APIRouter, HTTPException

from app.container import container
from app.domain.document import DocumentRecord

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentRecord])
def list_documents() -> list[DocumentRecord]:
    return container.document_repository.list()


@router.get("/{document_id}", response_model=DocumentRecord)
def get_document(document_id: str) -> DocumentRecord:
    document = container.document_repository.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
