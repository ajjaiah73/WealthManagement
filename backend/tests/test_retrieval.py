from pathlib import Path

import pytest

from app.domain.product import ProductType
from app.domain.retrieval import RetrievalMethod
from app.mock_data.clients import SEED_CLIENTS
from app.mock_data.documents import SEED_DOCUMENTS
from app.mock_data.products import SEED_PRODUCTS
from app.repositories.document_repository import InMemoryDocumentRepository
from app.repositories.product_repository import InMemoryProductRepository
from app.retrieval.bm25 import BM25Index
from app.retrieval.chunking import chunk_document
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.graph import NetworkxGraphStore, candidate_product_types, derive_topics
from app.retrieval.hybrid import HybridRetrievalConfig, HybridRetrievalService

CLIENTS = {c.client_id: c for c in SEED_CLIENTS}
MODELS_DIR = Path(__file__).resolve().parents[1] / "data" / "models"


def test_rrf_rewards_agreement_across_rankings() -> None:
    fused = reciprocal_rank_fusion({"a": ["x", "y", "z"], "b": ["y", "x"], "c": ["y"]})
    assert [key for key, _, _ in fused] == ["y", "x", "z"]
    top_key, top_score, sources = fused[0]
    assert sources == ["a", "b", "c"]
    assert top_score == pytest.approx(1 / 62 + 1 / 61 + 1 / 61)


def test_bm25_finds_cap_legislation() -> None:
    chunks = [c for d in SEED_DOCUMENTS for c in chunk_document(d)]
    hits = BM25Index(chunks).search("concessional contributions cap", limit=3)
    assert hits[0][0].document_id == "DOC-014"


def test_graph_topics_follow_client_facts() -> None:
    topics = derive_topics(CLIENTS["C-0002"], "Recommend a strategy")  # 58, high growth
    assert {"allocation_over_55", "fees", "disclosure"} <= set(topics)
    assert ProductType.CHOICE in candidate_product_types(CLIENTS["C-0002"], "")


def test_networkx_graph_reaches_governing_documents() -> None:
    store = NetworkxGraphStore()
    store.build(list(SEED_PRODUCTS), list(SEED_DOCUMENTS))
    hits = store.related_documents(["allocation_over_55"], [ProductType.TTR])
    by_id = {h.document_id: h for h in hits}
    assert hits[0].document_id == "DOC-017"
    assert "DOC-016" in by_id  # TTR -> preservation topic -> SIS Regulations
    assert any("Topic:allocation_over_55" in p for p in by_id["DOC-017"].paths)


@pytest.mark.skipif(not MODELS_DIR.exists(), reason="fastembed models not cached locally")
def test_hybrid_retrieval_end_to_end_with_real_models() -> None:
    service = HybridRetrievalService(
        InMemoryDocumentRepository(list(SEED_DOCUMENTS)),
        InMemoryProductRepository(list(SEED_PRODUCTS)),
        HybridRetrievalConfig(
            models_dir=str(MODELS_DIR), embedding_model="BAAI/bge-small-en-v1.5",
            reranker_model="Xenova/ms-marco-MiniLM-L-6-v2", qdrant_url=None, qdrant_path=":memory:",
            qdrant_collection="test", neo4j_uri=None, neo4j_user="neo4j", neo4j_password=None,
        ),
    )
    docs, trace = service.retrieve_with_trace(CLIENTS["C-0003"], "Transition to retirement income stream", 5)
    status = service.status()
    service.close()

    assert status["errors"] == {}
    assert status["dense"] == "qdrant-embedded" and status["graph"] == "networkx"
    assert {"dense", "bm25", "graph"} <= set(trace.counts)
    assert len(docs) == 5 and [d.rank for d in docs] == [1, 2, 3, 4, 5]
    assert "DOC-016" in [d.document_id for d in docs]  # preservation / TTR legislation
    assert all(d.retrieval_method == RetrievalMethod.FUSED and d.retrieval_sources for d in docs)
    assert all(0.0 <= d.rerank_score <= 1.0 for d in docs)
