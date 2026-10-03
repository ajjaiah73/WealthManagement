"""Retrieval service contract plus the offline mock used in tests.

The production implementation is app.retrieval.hybrid.HybridRetrievalService
(dense + BM25 + knowledge graph, RRF fusion, cross-encoder rerank). The mock
below is only selected with RETRIEVAL_BACKEND=mock so unit tests run without
model files; it is clearly labelled as such in /api/health.
"""
from typing import Any, Protocol

from app.domain.client import ClientProfile
from app.domain.retrieval import RetrievalMethod, RetrievedDocument
from app.repositories.base import DocumentSource
from app.retrieval.hybrid import RetrievalTrace


class RetrievalService(Protocol):
    def retrieve(self, profile: ClientProfile, query: str, top_k: int = 5) -> list[RetrievedDocument]: ...

    def retrieve_with_trace(
        self, profile: ClientProfile, query: str, top_k: int = 5
    ) -> tuple[list[RetrievedDocument], RetrievalTrace]: ...

    def status(self) -> dict[str, Any]: ...


class MockRetrievalService:
    def __init__(self, document_repository: DocumentSource) -> None:
        self._documents = document_repository

    def status(self) -> dict[str, Any]:
        return {"mode": "mock", "ready": True}

    def retrieve(self, profile: ClientProfile, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        return self.retrieve_with_trace(profile, query, top_k)[0]

    def retrieve_with_trace(
        self, profile: ClientProfile, query: str, top_k: int = 5
    ) -> tuple[list[RetrievedDocument], RetrievalTrace]:
        docs = self._documents.list()[:top_k]
        results: list[RetrievedDocument] = []
        for rank, doc in enumerate(docs, start=1):
            results.append(
                RetrievedDocument(
                    citation_id=f"CIT-{doc.document_id}-{rank}",
                    source=doc.document_type.value,
                    document=doc.title,
                    document_id=doc.document_id,
                    page=None,
                    section=None,
                    snippet=doc.full_text_excerpt[:240],
                    retrieval_method=RetrievalMethod.FUSED,
                    rank=rank,
                    rerank_score=round(max(0.99 - rank * 0.07, 0.5), 2),
                )
            )
        trace = RetrievalTrace(query=query, expanded_query=query, counts={"mock": len(results)})
        return results, trace
