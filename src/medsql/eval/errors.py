"""Analyse automatique des erreurs : pourquoi une réponse fausse est fausse.

Chaque réponse fausse reçoit **une** cause, la première qui s'applique dans l'ordre de
``ERROR_TYPES`` : on part des causes structurelles (le modèle n'a pas interrogé la bonne
table) pour finir par les symptômes (le bon nombre de lignes, mais pas les bonnes valeurs).
La comparaison se fait entre la requête générée et la requête de référence, analysées par
sqlglot ; les nombres de lignes viennent du run enregistré. Rien n'est réexécuté : l'analyse
s'applique donc aussi aux runs anciens.
"""

from __future__ import annotations

import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

ERROR_TYPES: tuple[tuple[str, str], ...] = (
    ("erreur_llm", "Pas de réponse du modèle (délai, panne)"),
    ("sql_invalide", "SQL non exécutable, même après auto-correction"),
    ("table_manquante", "Table nécessaire absente de la requête"),
    ("jointure", "Table en trop ou jointure sur d'autres colonnes"),
    ("agregat", "Agrégat différent (COUNT, COUNT DISTINCT, SUM, AVG…)"),
    ("filtre_texte", "Valeur de filtre texte différente"),
    ("lignes_en_trop", "Plus de lignes que la référence"),
    ("lignes_manquantes", "Moins de lignes que la référence"),
    ("valeurs", "Bon nombre de lignes, valeurs différentes"),
)
ERROR_LABELS: dict[str, str] = dict(ERROR_TYPES)

_AGGREGATES: tuple[type[exp.Expression], ...] = (exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max)


@dataclass(frozen=True)
class SqlShape:
    """Ce qui compte pour comparer deux requêtes : tables, jointures, agrégats, textes."""

    tables: frozenset[str]
    join_keys: frozenset[frozenset[str]]
    aggregates: tuple[str, ...]
    literals: frozenset[str]


def _fold(text: str) -> str:
    """Majuscules sans accents ni jokers : 'Rupture de stock' ≈ '%RUPTURE DE STOCK%'."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return plain.replace("%", "").strip().upper()


def _aggregate_name(node: exp.Expression) -> str:
    name = type(node).__name__.upper()
    if isinstance(node, exp.Count) and isinstance(node.this, exp.Distinct):
        return "COUNT DISTINCT"
    return name


def sql_shape(sql: str) -> SqlShape | None:
    """Analyse une requête SQLite ; ``None`` si sqlglot ne sait pas la lire."""
    try:
        tree = sqlglot.parse_one(sql, read="sqlite")
    except SqlglotError:
        return None
    if tree is None:
        return None
    ctes = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    tables = frozenset(
        t.name.lower() for t in tree.find_all(exp.Table) if t.name.lower() not in ctes
    )
    join_keys = set()
    for join in tree.find_all(exp.Join):
        on = join.args.get("on")
        if on is None:
            continue
        for eq in on.find_all(exp.EQ):
            cols = [c.name.lower() for c in eq.find_all(exp.Column)]
            if len(cols) == 2:
                join_keys.add(frozenset(cols))
    aggregates = tuple(sorted(_aggregate_name(n) for n in tree.find_all(*_AGGREGATES)))
    literals = frozenset(
        _fold(lit.this) for lit in tree.find_all(exp.Literal) if lit.is_string and lit.this
    )
    return SqlShape(tables, frozenset(join_keys), aggregates, literals)


def classify(item: Mapping[str, Any]) -> str | None:  # noqa: PLR0911 (une sortie par cause)
    """Cause de l'erreur d'une réponse du run, ``None`` si la réponse est juste."""
    if item.get("correct"):
        return None
    error = item.get("error") or ""
    if error.startswith("LLMError"):
        return "erreur_llm"
    if not item.get("executable") or not item.get("pred_sql"):
        return "sql_invalide"
    gold, pred = sql_shape(item["gold_sql"]), sql_shape(item["pred_sql"])
    if gold is not None and pred is not None:
        if gold.tables - pred.tables:
            return "table_manquante"
        if pred.tables - gold.tables or gold.join_keys != pred.join_keys:
            return "jointure"
        if gold.aggregates != pred.aggregates:
            return "agregat"
        if gold.literals != pred.literals:
            return "filtre_texte"
    gold_rows, pred_rows = item.get("gold_rows"), item.get("pred_rows")
    if gold_rows is not None and pred_rows is not None:
        if pred_rows > gold_rows:
            return "lignes_en_trop"
        if pred_rows < gold_rows:
            return "lignes_manquantes"
    return "valeurs"


def error_breakdown(items: Iterable[Mapping[str, Any]]) -> dict[str, list[str]]:
    """Identifiants des questions fausses, regroupés par cause (dans l'ordre de ERROR_TYPES)."""
    found: dict[str, list[str]] = {key: [] for key, _ in ERROR_TYPES}
    for item in items:
        cause = classify(item)
        if cause is not None:
            found[cause].append(str(item["id"]))
    return {key: ids for key, ids in found.items() if ids}


def error_counts(items: Iterable[Mapping[str, Any]]) -> Counter[str]:
    return Counter({key: len(ids) for key, ids in error_breakdown(items).items()})
