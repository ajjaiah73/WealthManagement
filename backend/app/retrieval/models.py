"""Local ONNX models (fastembed) for embeddings and cross-encoder reranking.

Models are cached under settings.models_dir. Loading tries the local cache
first (no network); only if the model is absent does it download, using the
OS trust store so corporate TLS-inspecting proxies work.
"""
import logging
import math
from collections.abc import Callable

from fastembed import TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder

logger = logging.getLogger(__name__)

def _load[M](factory: Callable[..., M], model_name: str, cache_dir: str) -> M:
    try:
        return factory(model_name=model_name, cache_dir=cache_dir, local_files_only=True)
    except Exception:  # noqa: BLE001 - any cache miss falls through to a download attempt
        logger.info("Model %s not in local cache; downloading", model_name)
    try:
        import truststore

        truststore.inject_into_ssl()
    except ImportError:  # pragma: no cover - optional
        pass
    return factory(model_name=model_name, cache_dir=cache_dir)


class Embedder:
    def __init__(self, model_name: str, cache_dir: str) -> None:
        self.model_name = model_name
        self._model = _load(TextEmbedding, model_name, cache_dir)
        self.dimension = len(next(iter(self._model.query_embed(["dimension probe"]))))

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.passage_embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return next(iter(self._model.query_embed([text]))).tolist()


class Reranker:
    def __init__(self, model_name: str, cache_dir: str) -> None:
        self.model_name = model_name
        self._model = _load(TextCrossEncoder, model_name, cache_dir)

    def score(self, query: str, passages: list[str]) -> list[float]:
        """Cross-encoder relevance logits squashed to (0, 1) with a sigmoid."""
        if not passages:
            return []
        return [1.0 / (1.0 + math.exp(-float(logit))) for logit in self._model.rerank(query, passages)]
