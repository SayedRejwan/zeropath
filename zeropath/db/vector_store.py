from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np


@dataclass(frozen=True)
class VectorMatch:
    id: str
    score: float
    metadata: dict[str, Any]


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


class InMemoryVectorStore:
    """
    Local-dev vector store.

    Stores vectors in memory and answers similarity queries via cosine similarity.
    """

    def __init__(self, *, dim: int):
        self._dim = dim
        self._vectors: dict[str, np.ndarray] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    @property
    def dim(self) -> int:
        return self._dim

    def upsert(self, *, vec_id: str, vector: list[float], metadata: Optional[dict[str, Any]] = None) -> None:
        v = np.asarray(vector, dtype=np.float32)
        if v.shape != (self._dim,):
            raise ValueError(f"Vector dim mismatch: expected {self._dim}, got {v.shape}")
        self._vectors[vec_id] = v
        self._metadata[vec_id] = metadata or {}

    def query(self, *, vector: list[float], top_k: int = 5) -> list[VectorMatch]:
        q = np.asarray(vector, dtype=np.float32)
        if q.shape != (self._dim,):
            raise ValueError(f"Query dim mismatch: expected {self._dim}, got {q.shape}")

        matches: list[VectorMatch] = []
        for vec_id, v in self._vectors.items():
            score = _cosine_similarity(q, v)
            matches.append(VectorMatch(id=vec_id, score=score, metadata=self._metadata.get(vec_id, {})))

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:top_k]
