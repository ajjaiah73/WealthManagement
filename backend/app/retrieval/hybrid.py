"""Hybrid retrieval service: dense + BM25 + knowledge graph -> RRF -> cross-encoder rerank."""
import logging
import threading
from dataclasses import dataclass, field

from app.domain.client import ClientProfile
from app.domain.retrieval import RetrievalMethod, RetrievedDocument
from app.repositories.base import DocumentSource, ProductSource
from app.retrieval.bm25 import BM25Index
from app.retrieval.chunking import Chunk, chunk_document
from app.retrieval.dense import DenseIndex, make_qdrant_client
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.graph import (
    GraphHit,
    GraphStore,
    candidate_product_types,
    derive_topics,
    make_graph_store,
    topic_label,
)
from app.retrieval.models import Embedder, Reranker

logger = logging.getLogger(__name__)

_CANDIDATES_PER_METHOD = 12
_RERANK_POOL = 10
_RERANK_WEIGHT = 0.6


@dataclass
class RetrievalTrace:
    query: str
    expanded_query: str
    topics: dict[str, str] = field(default_factory=dict)
    product_types: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    backends: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        counts = ", ".join(f"{k}={v}" for k, v in self.counts.items())
        topics = ", ".join(topic_label(k) for k in self.topics)
        return f"{counts}; graph topics: {topics}"


@dataclass(frozen=True)
class HybridRetrievalConfig:
    models_dir: str
    embedding_model: str
    reranker_model: str
    qdrant_url: str | None
    qdrant_path: str
    qdrant_collection: str
    neo4j_uri: str | None
    neo4j_user: str
    neo4j_password: str | None


class HybridRetrievalService:
    def __init__(self, documents: DocumentSource, products: ProductSource, config: HybridRetrievalConfig) -> None:
        self._documents = documents
        self._products = products
        self._config = config
        self._lock = threading.Lock()
        self._ready = False
        self._chunks: dict[str, list[Chunk]] = {}
        self._bm25: BM25Index | None = None
        self._dense: DenseIndex | None = None
        self._reranker: Reranker | None = None
        self._graph: GraphStore | None = None
        self.errors: dict[str, str] = {}

    # -- lifecycle -----------------------------------------------------------------
    def warmup(self) -> None:
        with self._lock:
            self._ensure_ready()

    def _ensure_ready(self) -> None:
        if self._ready:
            return
        documents = self._documents.list()
        chunks = [c for d in documents for c in chunk_document(d)]
        self._chunks = {}
        for c in chunks:
            self._chunks.setdefault(c.document_id, []).append(c)
        self._bm25 = BM25Index(chunks)

        cfg = self._config
        # Each neural/infra component degrades independently: a missing model or an
        # unreachable Qdrant removes that signal from fusion instead of failing advice.
        try:
            embedder = Embedder(cfg.embedding_model, cfg.models_dir)
            self._dense = DenseIndex(make_qdrant_client(cfg.qdrant_url, cfg.qdrant_path), cfg.qdrant_collection,
                                     embedder)
            self._dense.index(chunks)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Dense retrieval unavailable")
            self.errors["dense"] = str(exc)
            self._dense = None
        try:
            self._reranker = Reranker(cfg.reranker_model, cfg.models_dir)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Cross-encoder reranker unavailable")
            self.errors["rerank"] = str(exc)
        try:
            self._graph = make_graph_store(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
            self._graph.build(self._products.list(), documents)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Knowledge graph unavailable")
            self.errors["graph"] = str(exc)
            self._graph = None
        self._ready = True
        logger.info("Hybrid retrieval ready: %s", self.status())

    def status(self) -> dict[str, object]:
        return {
            "mode": "hybrid",
            "ready": self._ready,
            "dense": self._dense.backend if self._dense else None,
            "embedding_model": self._config.embedding_model if self._dense else None,
            "bm25": "rank-bm25" if self._bm25 else None,
            "graph": self._graph.backend if self._graph else None,
            "reranker": self._config.reranker_model if self._reranker else None,
            "fusion": "rrf(k=60)",
            "chunks": sum(len(v) for v in self._chunks.values()),
            "errors": dict(self.errors),
        }

    def close(self) -> None:
        if self._dense:
            self._dense.close()
        if self._graph:
            self._graph.close()

    # -- retrieval -----------------------------------------------------------------
    def retrieve(self, profile: ClientProfile, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        return self.retrieve_with_trace(profile, query, top_k)[0]

    def retrieve_with_trace(
        self, profile: ClientProfile, query: str, top_k: int = 5
    ) -> tuple[list[RetrievedDocument], RetrievalTrace]:
        with self._lock:
            self._ensure_ready()
            return self._retrieve(profile, query, top_k)

    def _retrieve(
        self, profile: ClientProfile, query: str, top_k: int
    ) -> tuple[list[RetrievedDocument], RetrievalTrace]:
        topics = derive_topics(profile, query)
        product_types = candidate_product_types(profile, query)
        expanded = expand_query(profile, query, topics)
        trace = RetrievalTrace(
            query=query, expanded_query=expanded, topics=topics, product_types=[t.value for t in product_types],
            backends={k: str(v) for k, v in self.status().items() if k in ("dense", "graph", "reranker")},
        )

        best_chunk: dict[str, Chunk] = {}
        rankings: dict[str, list[str]] = {}

        if self._dense is not None:
            dense_docs = _dedupe_docs(self._dense.search(expanded, _CANDIDATES_PER_METHOD), best_chunk)
            rankings[RetrievalMethod.DENSE.value] = dense_docs
        if self._bm25 is not None:
            bm25_docs = _dedupe_docs(self._bm25.search(expanded, _CANDIDATES_PER_METHOD), best_chunk)
            rankings[RetrievalMethod.BM25.value] = bm25_docs
        graph_hits: dict[str, GraphHit] = {}
        if self._graph is not None:
            hits = self._graph.related_documents(list(topics), product_types)[:_CANDIDATES_PER_METHOD]
            graph_hits = {h.document_id: h for h in hits}
            rankings[RetrievalMethod.GRAPH.value] = [h.document_id for h in hits]
        trace.counts = {name: len(docs) for name, docs in rankings.items()}

        fused = reciprocal_rank_fusion(rankings)[:_RERANK_POOL]
        candidates = [
            (doc_id, score, sources, best_chunk.get(doc_id) or self._chunks.get(doc_id, [None])[0])
            for doc_id, score, sources in fused
        ]
        candidates = [c for c in candidates if c[3] is not None]

        if self._reranker is not None and candidates:
            rerank_scores = self._reranker.score(expanded, [c[3].indexed_text for c in candidates])  # type: ignore[union-attr]
        else:
            # No cross-encoder: fall back to the normalised fused score.
            top = candidates[0][1] if candidates else 1.0
            rerank_scores = [c[1] / top for c in candidates]
        trace.counts["fused"] = len(candidates)

        # Final order blends the cross-encoder with normalised RRF, so documents the
        # knowledge graph ties to the client's facts aren't discarded purely on
        # passage-level lexical/semantic fit.
        top_fused = candidates[0][1] if candidates else 1.0
        blended = [
            _RERANK_WEIGHT * r + (1 - _RERANK_WEIGHT) * (c[1] / top_fused)
            for c, r in zip(candidates, rerank_scores, strict=True)
        ]
        ranked = sorted(
            zip(candidates, rerank_scores, blended, strict=True), key=lambda triple: triple[2], reverse=True
        )
        results: list[RetrievedDocument] = []
        for rank, ((doc_id, fusion_score, sources, chunk), rerank_score, _) in enumerate(ranked[:top_k], start=1):
            assert chunk is not None
            hit = graph_hits.get(doc_id)
            results.append(RetrievedDocument(
                citation_id=f"CIT-{doc_id}-{rank}",
                source=chunk.source,
                document=chunk.title,
                document_id=doc_id,
                page=None,
                section=chunk.section,
                snippet=chunk.text[:400],
                retrieval_method=RetrievalMethod.FUSED,
                rank=rank,
                rerank_score=round(float(rerank_score), 4),
                retrieval_sources=[RetrievalMethod(s) for s in sources],
                fusion_score=round(fusion_score, 5),
                graph_paths=list(hit.paths[:3]) if hit else [],
            ))
        return results, trace


def _dedupe_docs(hits: list[tuple[Chunk, float]], best_chunk: dict[str, Chunk]) -> list[str]:
    """Collapses a chunk ranking to a document ranking (first = best chunk)."""
    seen: list[str] = []
    for chunk, _ in hits:
        if chunk.document_id not in seen:
            seen.append(chunk.document_id)
            best_chunk.setdefault(chunk.document_id, chunk)
    return seen


def expand_query(profile: ClientProfile, query: str, topics: dict[str, str]) -> str:
    facts: list[str] = []
    if profile.age is not None:
        facts.append(f"member aged {profile.age}")
    if profile.risk_tolerance is not None:
        facts.append(f"{profile.risk_tolerance.value} risk profile")
    if profile.target_retirement_age is not None:
        facts.append(f"retiring at {profile.target_retirement_age}")
    topic_text = "; ".join(topic_label(k) for k in topics)
    return f"{query}. {', '.join(facts)}. Relevant: {topic_text}."
