"""Dense vector retrieval over Qdrant.

Qdrant runs as a server when QDRANT_URL is set (docker-compose), otherwise as
qdrant-client's embedded local store at QDRANT_PATH (":memory:" in tests).
"""
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.retrieval.chunking import Chunk
from app.retrieval.models import Embedder


def make_qdrant_client(url: str | None, path: str) -> QdrantClient:
    if url:
        return QdrantClient(url=url, timeout=10)
    if path == ":memory:":
        return QdrantClient(location=":memory:")
    return QdrantClient(path=path)


class DenseIndex:
    def __init__(self, client: QdrantClient, collection: str, embedder: Embedder) -> None:
        self._client = client
        self._collection = collection
        self._embedder = embedder
        self._chunks: dict[str, Chunk] = {}

    @property
    def backend(self) -> str:
        return "qdrant-server" if self._client.init_options.get("url") else "qdrant-embedded"

    def index(self, chunks: list[Chunk]) -> None:
        """(Re)builds the collection from the current document corpus. The corpus is
        small, so a full rebuild at startup keeps vectors in lockstep with the
        documents table and the embedding model."""
        if self._client.collection_exists(self._collection):
            self._client.delete_collection(self._collection)
        self._client.create_collection(
            self._collection,
            vectors_config=VectorParams(size=self._embedder.dimension, distance=Distance.COSINE),
        )
        vectors = self._embedder.embed_passages([c.indexed_text for c in chunks])
        self._client.upsert(
            self._collection,
            points=[
                PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, chunk.chunk_id)),
                    vector=vector,
                    payload={"chunk_id": chunk.chunk_id, "document_id": chunk.document_id, "title": chunk.title},
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            ],
            wait=True,
        )
        self._chunks = {c.chunk_id: c for c in chunks}

    def search(self, query: str, limit: int = 20) -> list[tuple[Chunk, float]]:
        response = self._client.query_points(
            self._collection, query=self._embedder.embed_query(query), limit=limit, with_payload=True
        )
        results: list[tuple[Chunk, float]] = []
        for point in response.points:
            chunk = self._chunks.get(str((point.payload or {}).get("chunk_id")))
            if chunk is not None:
                results.append((chunk, float(point.score)))
        return results

    def close(self) -> None:
        self._client.close()
