"""Cache des requêtes générées (S12).

Une question déjà posée n'a pas besoin du LLM : on garde la **requête SQL** produite, pas son
résultat, et on la réexécute (quelques millisecondes). La réponse suit donc toujours la base du
jour, même après une mise à jour de la BDPM. Une abstention est gardée aussi.

La clé ignore la casse, les accents, les espaces et la ponctuation finale : « Combien de
médicaments ? » et « combien de medicaments » partagent leur entrée. Elle inclut le modèle et
la configuration du prompt : changer de modèle ne réutilise pas les requêtes d'un autre.
Le cache sert la démo ; l'évaluation ne l'utilise pas.
"""

from __future__ import annotations

import re
from collections import OrderedDict

from medsql.sql_guard import sans_accents

DEFAULT_SIZE = 256


def normalize_question(question: str) -> str:
    folded = sans_accents(question) or ""
    folded = re.sub(r"[\s  ]+", " ", folded).strip()
    return folded.rstrip(" ?!.;:").strip()


class QueryCache:
    """Cache LRU : clé (modèle, configuration, question normalisée) → requête SQL."""

    def __init__(self, size: int = DEFAULT_SIZE) -> None:
        self.size = size
        self._entries: OrderedDict[tuple[str, str, str], str] = OrderedDict()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def key(model: str, config: str, question: str) -> tuple[str, str, str]:
        return (model, config, normalize_question(question))

    def get(self, key: tuple[str, str, str]) -> str | None:
        sql = self._entries.get(key)
        if sql is None:
            self.misses += 1
            return None
        self._entries.move_to_end(key)
        self.hits += 1
        return sql

    def put(self, key: tuple[str, str, str], sql: str) -> None:
        self._entries[key] = sql
        self._entries.move_to_end(key)
        while len(self._entries) > self.size:
            self._entries.popitem(last=False)

    def discard(self, key: tuple[str, str, str]) -> None:
        self._entries.pop(key, None)

    def __len__(self) -> int:
        return len(self._entries)
