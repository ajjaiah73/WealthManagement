"""Sparse lexical retrieval with Okapi BM25 (rank-bm25)."""
from rank_bm25 import BM25Okapi

from app.retrieval.chunking import Chunk, tokenize


class BM25Index:
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks
        self._bm25 = BM25Okapi([tokenize(c.indexed_text) for c in chunks]) if chunks else None

    def search(self, query: str, limit: int = 20) -> list[tuple[Chunk, float]]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(zip(self._chunks, scores, strict=True), key=lambda pair: pair[1], reverse=True)
        return [(chunk, float(score)) for chunk, score in ranked[:limit] if score > 0]
