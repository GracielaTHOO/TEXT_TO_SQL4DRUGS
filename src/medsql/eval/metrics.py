"""Comparaison des résultats d'exécution (métrique principale : *execution accuracy*).

Deux niveaux de sévérité :

- **strict** : mêmes lignes, mêmes colonnes dans le même ordre (multiensemble de lignes,
  ordre des lignes pris en compte seulement si la question l'exige) ;
- **souple** (métrique de référence du projet) : la prédiction peut contenir des colonnes
  supplémentaires ou réordonnées. On cherche une projection des colonnes prédites qui
  reproduit exactement le résultat de référence. Une réponse « DOLIPRANE + son code CIS »
  à la question « quels médicaments… » est donc juste ; une réponse avec des lignes
  en trop ou en moins ne l'est pas.

Normalisation des valeurs : chaînes nettoyées, nombres arrondis à 1 décimale (un modèle
qui arrondit 37,12 % en 37,1 % ne doit pas être pénalisé), ``1`` ≡ ``1.0``.
"""

from __future__ import annotations

import itertools
from collections import Counter
from collections.abc import Sequence

Value = object
Rows = Sequence[Sequence[Value]]

MAX_ASSIGNMENTS = 5_000


def normalize_value(value: Value) -> Value:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return round(float(value), 1) + 0.0  # + 0.0 : évite -0.0
    if isinstance(value, str):
        return value.strip()
    return value


def _norm_rows(rows: Rows) -> list[tuple[Value, ...]]:
    return [tuple(normalize_value(v) for v in row) for row in rows]


def _same(gold: list[tuple[Value, ...]], pred: list[tuple[Value, ...]], ordered: bool) -> bool:
    if ordered:
        return gold == pred
    return Counter(gold) == Counter(pred)


def strict_match(gold: Rows, pred: Rows, *, ordered: bool = False) -> bool:
    return _same(_norm_rows(gold), _norm_rows(pred), ordered)


def soft_match(gold: Rows, pred: Rows, *, ordered: bool = False) -> bool:  # noqa: PLR0911
    """Vrai s'il existe une projection des colonnes prédites égale au résultat de référence."""
    g, p = _norm_rows(gold), _norm_rows(pred)
    if len(g) != len(p):
        return False
    if not g:
        return True
    n_gold, n_pred = len(g[0]), len(p[0])
    if n_pred < n_gold:
        return False
    if _same(g, p, ordered):
        return True

    # Candidats par colonne : mêmes valeurs (en multiensemble) que la colonne de référence.
    gold_cols = [Counter(row[j] for row in g) for j in range(n_gold)]
    pred_cols = [Counter(row[k] for row in p) for k in range(n_pred)]
    candidates = [[k for k in range(n_pred) if pred_cols[k] == gold_cols[j]] for j in range(n_gold)]
    if any(not c for c in candidates):
        return False

    for count, assignment in enumerate(itertools.product(*candidates)):
        if count >= MAX_ASSIGNMENTS:
            break
        if len(set(assignment)) != len(assignment):
            continue
        projected = [tuple(row[k] for k in assignment) for row in p]
        if _same(g, projected, ordered):
            return True
    return False
