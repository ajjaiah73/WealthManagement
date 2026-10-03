"""Reciprocal Rank Fusion (Cormack et al., 2009)."""
from collections import defaultdict
from collections.abc import Hashable, Mapping, Sequence

RRF_K = 60


def reciprocal_rank_fusion[K: Hashable](
    rankings: Mapping[str, Sequence[K]], k: int = RRF_K
) -> list[tuple[K, float, list[str]]]:
    """Fuses several ranked lists of keys. Returns (key, fused score, contributing
    ranking names), best first. score(d) = sum over lists of 1 / (k + rank(d))."""
    scores: dict[K, float] = defaultdict(float)
    sources: dict[K, list[str]] = defaultdict(list)
    for name, ranking in rankings.items():
        for rank, key in enumerate(ranking, start=1):
            scores[key] += 1.0 / (k + rank)
            sources[key].append(name)
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [(key, score, sources[key]) for key, score in ordered]
