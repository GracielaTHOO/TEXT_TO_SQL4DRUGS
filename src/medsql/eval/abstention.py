"""Abstention : le modèle sait-il dire « cette base ne répond pas à cette question » ?

Une partie du jeu est **hors périmètre** (posologie, effets indésirables, ventes, demande de
modification, sujet sans rapport…) : la seule bonne réponse est de s'abstenir, sans exécuter
de requête. Deux erreurs symétriques :

- une **abstention manquée** : le modèle invente une requête pour une question sans réponse
  dans la base (le résultat affiché serait trompeur) ;
- une **abstention à tort** : le modèle refuse une question à laquelle la base répond.

L'exactitude d'exécution reste calculée sur les seules questions du périmètre, pour rester
comparable d'un jeu à l'autre ; l'abstention est mesurée à part.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def answerable(items: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Réponses aux seules questions du périmètre (les runs anciens n'ont pas la clé)."""
    return [i for i in items if not i.get("hors_perimetre")]


def abstention_stats(items: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    """Bilan d'abstention d'un run ; vide s'il ne contient aucune question hors périmètre."""
    rows = list(items)
    outside = [i for i in rows if i.get("hors_perimetre")]
    if not outside:
        return {}
    inside = answerable(rows)
    correct = sum(bool(i.get("abstained")) for i in outside)
    false = sum(bool(i.get("abstained")) for i in inside)
    return {
        "out_of_scope": len(outside),
        "correct": correct,
        "rate": correct / len(outside),
        "in_scope": len(inside),
        "false_abstentions": false,
        "false_rate": false / len(inside) if inside else 0.0,
    }
