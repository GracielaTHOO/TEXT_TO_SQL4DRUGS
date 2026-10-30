"""Sélection dynamique des exemples few-shot par similarité (S10).

Les trois exemples fixes du prompt ne ressemblent pas forcément à la question posée. Ici, une
réserve d'exemples (``examples.yaml``, disjointe du jeu d'évaluation) est encodée une fois ;
pour chaque question, on retient les ``k`` exemples dont l'embedding est le plus proche
(similarité cosinus). L'exemple d'abstention reste toujours présent, pour que la comparaison
avec les exemples fixes ne porte que sur le choix des exemples SQL.

Deux encodeurs locaux :

- ``OllamaEmbedder`` : modèle d'embeddings servi par Ollama (``nomic-embed-text`` par défaut) ;
- ``LexicalEmbedder`` : sac de trigrammes de caractères, sans modèle ni dépendance. Sert aux
  tests et de référence simple (« ressemble par les mots »).
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Protocol

import httpx
import yaml

from medsql.sql_guard import sans_accents

DEFAULT_K = 3
LEXICAL_DIM = 4096


@dataclass(frozen=True)
class Example:
    question: str
    sql: str


def default_pool_path() -> Path:
    return Path(str(resources.files("medsql").joinpath("examples.yaml")))


def load_pool(path: Path | None = None) -> list[Example]:
    raw = yaml.safe_load((path or default_pool_path()).read_text("utf-8"))
    pool = [Example(str(r["question"]).strip(), str(r["sql"]).strip()) for r in raw]
    if len({e.question.lower() for e in pool}) != len(pool):
        raise ValueError("Questions dupliquées dans la réserve d'exemples.")
    return pool


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class LexicalEmbedder:
    """Trigrammes de caractères (sans accents, majuscules), hachés dans un vecteur fixe."""

    name = "lexical"

    def __init__(self, dim: int = LEXICAL_DIM) -> None:
        self.dim = dim

    def _vector(self, text: str) -> list[float]:
        folded = f"  {sans_accents(text) or ''}  "
        vector = [0.0] * self.dim
        for i in range(len(folded) - 2):
            digest = hashlib.blake2b(folded[i : i + 3].encode(), digest_size=4).digest()
            vector[int.from_bytes(digest, "big") % self.dim] += 1.0
        return vector

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]


class OllamaEmbedder:
    """Embeddings servis par Ollama (API ``/api/embed``)."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        timeout_s: float = 60,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.name = model
        self._client = httpx.Client(base_url=base_url, timeout=timeout_s, transport=transport)

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.post("/api/embed", json={"model": self.name, "input": texts})
        response.raise_for_status()
        return [[float(x) for x in v] for v in response.json()["embeddings"]]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


class ExampleSelector:
    """Choisit, pour une question, les ``k`` exemples les plus proches de la réserve."""

    def __init__(self, embedder: Embedder, pool: list[Example] | None = None, k: int = DEFAULT_K):
        self.embedder = embedder
        self.pool = pool if pool is not None else load_pool()
        self.k = k
        self._vectors = embedder.embed([e.question for e in self.pool])

    def scored(self, question: str) -> list[tuple[float, Example]]:
        """Exemples triés du plus au moins proche (à égalité, ordre de la réserve)."""
        (query,) = self.embedder.embed([question])
        scores = [cosine(query, v) for v in self._vectors]
        order = sorted(range(len(self.pool)), key=lambda i: (-scores[i], i))
        return [(scores[i], self.pool[i]) for i in order]

    def select(self, question: str) -> list[Example]:
        """Les ``k`` plus proches, le plus proche en dernier (juste avant la question)."""
        best = [e for _, e in self.scored(question)[: self.k]]
        return best[::-1]
