"""Robustesse à la formulation : une question et sa reformulation ont-elles le même sort ?

Chaque reformulation (``paraphrase_de``) partage la requête de référence de sa source. On
compte, sur les paires présentes dans un run, les quatre issues possibles. Deux indicateurs :

- ``consistency`` : part des paires où les deux formulations sont justes ou fausses ensemble ;
- ``kept`` : part des sources justes dont la reformulation reste juste (une réponse juste
  qui ne tient qu'à la formulation exacte n'est pas une compétence).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def robustness(items: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    """Bilan des paires (source, reformulation) d'un run ; vide s'il n'y en a aucune."""
    rows = list(items)
    correct = {str(i["id"]): bool(i["correct"]) for i in rows}
    pairs = [
        (correct[str(i["paraphrase_de"])], bool(i["correct"]))
        for i in rows
        if i.get("paraphrase_de") and str(i["paraphrase_de"]) in correct
    ]
    if not pairs:
        return {}
    both = sum(o and p for o, p in pairs)
    only_original = sum(o and not p for o, p in pairs)
    only_paraphrase = sum(p and not o for o, p in pairs)
    neither = len(pairs) - both - only_original - only_paraphrase
    return {
        "pairs": len(pairs),
        "both": both,
        "only_original": only_original,
        "only_paraphrase": only_paraphrase,
        "neither": neither,
        "consistency": (both + neither) / len(pairs),
        "kept": both / (both + only_original) if both + only_original else 0.0,
    }
