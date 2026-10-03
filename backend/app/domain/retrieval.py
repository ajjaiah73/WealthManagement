from enum import Enum

from pydantic import BaseModel, Field


class RetrievalMethod(str, Enum):
    DENSE = "dense"
    BM25 = "bm25"
    GRAPH = "graph"
    FUSED = "fused"


class RetrievedDocument(BaseModel):
    citation_id: str
    source: str  # e.g. "PDS", "Regulatory Guidance", "Legislation"
    document: str
    document_id: str
    page: int | None = None
    section: str | None = None
    snippet: str
    retrieval_method: RetrievalMethod
    rank: int
    rerank_score: float
    # Which retrievers surfaced this document before fusion, its RRF score, and the
    # knowledge-graph paths that reached it (empty when the graph didn't).
    retrieval_sources: list[RetrievalMethod] = Field(default_factory=list)
    fusion_score: float | None = None
    graph_paths: list[str] = Field(default_factory=list)
