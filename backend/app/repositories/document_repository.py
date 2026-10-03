
from app.domain.document import DocumentRecord


class InMemoryDocumentRepository:
    def __init__(self, documents: list[DocumentRecord]) -> None:
        self._documents: dict[str, DocumentRecord] = {d.document_id: d for d in documents}

    def get(self, document_id: str) -> DocumentRecord | None:
        return self._documents.get(document_id)

    def list(self) -> list[DocumentRecord]:
        return list(self._documents.values())

    def add(self, document: DocumentRecord) -> DocumentRecord:
        self._documents[document.document_id] = document
        return document
