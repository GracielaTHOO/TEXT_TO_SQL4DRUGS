"""Construction du prompt Text-to-SQL.

Choix de conception :
- le schéma complet est fourni (12 tables, ~4 k tokens) : pas de sélection de tables
  approximative qui ferait échouer les jointures ;
- les règles métier propres à la BDPM sont explicites (majuscules accentuées, dates ISO…) ;
- les exemples few-shot sont **disjoints** du jeu d'évaluation (vérifié par un test) ;
- en option, les libellés exacts des colonnes catégorielles sont lus dans la base et ajoutés
  au schéma, pour que le modèle ne devine pas « Rupture » au lieu de « Rupture de stock ».
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from medsql.data.schema import CATEGORICAL, schema_for_prompt
from medsql.llm.base import Message

SYSTEM_RULES = """\
Tu es un expert SQL. Tu traduis des questions en français en UNE requête SQLite \
qui interroge la Base de données publique des médicaments (BDPM, ANSM).

Règles :
1. Réponds uniquement par la requête, dans un bloc ```sql```, sans explication.
2. Lecture seule : uniquement SELECT (ou WITH … SELECT).
3. Recherche textuelle : les noms sont en MAJUSCULES accentuées. Utilise toujours
   sans_accents(colonne) LIKE '%MOT SANS ACCENT EN MAJUSCULES%'.
   Exemple : sans_accents(c.substance) LIKE '%PARACETAMOL%'.
4. Les dates sont des chaînes ISO 'AAAA-MM-JJ' : utilise strftime('%Y', date) ou des comparaisons de chaînes.
5. Une spécialité = un code CIS (table medicaments). Une boîte = un CIP13 (table presentations).
   Pour compter des médicaments, compte les CIS distincts : COUNT(DISTINCT m.cis).
6. « Commercialisé » signifie medicaments.etat_commercialisation = 'Commercialisée'.
7. « Remboursé » signifie presentations.taux_remboursement IS NOT NULL.
8. Une substance active est une ligne de compositions avec nature_composant = 'SA'.
9. Ne renvoie que les colonnes utiles à la question, avec des alias lisibles.
10. N'ajoute pas de LIMIT sauf si la question demande un nombre précis de résultats (« les 5… »).
"""

FEW_SHOTS: tuple[tuple[str, str], ...] = (
    (
        "Combien de spécialités sont commercialisées par le laboratoire BIOGARAN ?",
        "SELECT COUNT(DISTINCT cis) AS nb_specialites\n"
        "FROM medicaments\n"
        "WHERE etat_commercialisation = 'Commercialisée'\n"
        "  AND sans_accents(titulaires) LIKE '%BIOGARAN%'",
    ),
    (
        "Quels médicaments contiennent de la cétirizine ?",
        "SELECT DISTINCT m.cis, m.denomination\n"
        "FROM medicaments m\n"
        "JOIN compositions c ON c.cis = m.cis\n"
        "WHERE c.nature_composant = 'SA'\n"
        "  AND sans_accents(c.substance) LIKE '%CETIRIZINE%'",
    ),
    (
        "Quel est le prix moyen d'une boîte remboursée à 30 % ?",
        "SELECT ROUND(AVG(prix_euros), 2) AS prix_moyen_euros\n"
        "FROM presentations\n"
        "WHERE taux_remboursement = 30 AND prix_euros IS NOT NULL",
    ),
)


# Au-delà, une colonne est un texte libre (formes, conditions) : ses libellés ne sont pas listés.
MAX_HINT_VALUES = 12


@dataclass(frozen=True)
class PromptConfig:
    few_shot: bool = True
    value_hints: bool = False


def _sql_literal(value: object) -> str:
    """Littéral SQL tel que le modèle doit l'écrire : 'Tension d''approvisionnement'."""
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return str(value)


def value_hints(conn: sqlite3.Connection) -> str:
    """Libellés exacts des colonnes catégorielles, du plus au moins fréquent."""
    lines = []
    for table, column in CATEGORICAL:
        try:
            values = [
                row[0]
                for row in conn.execute(
                    f"SELECT {column} FROM {table} WHERE {column} IS NOT NULL "
                    f"GROUP BY {column} ORDER BY COUNT(*) DESC LIMIT {MAX_HINT_VALUES + 1}"
                )
            ]
        except sqlite3.OperationalError:  # table absente d'une base partielle
            continue
        if not values or len(values) > MAX_HINT_VALUES:
            continue
        shown = ", ".join(_sql_literal(v) for v in values)
        lines.append(f"- {table}.{column} : {shown}")
    if not lines:
        return ""
    return "Valeurs exactes des colonnes catégorielles (à utiliser telles quelles) :\n" + "\n".join(
        lines
    )


def build_messages(
    question: str, config: PromptConfig | None = None, *, hints: str = ""
) -> list[Message]:
    config = config or PromptConfig()
    system = f"{SYSTEM_RULES}\nSchéma de la base :\n\n{schema_for_prompt()}"
    if hints:
        system += f"\n\n{hints}"
    messages = [Message("system", system)]
    if config.few_shot:
        for q, sql in FEW_SHOTS:
            messages.append(Message("user", q))
            messages.append(Message("assistant", f"```sql\n{sql}\n```"))
    messages.append(Message("user", question.strip()))
    return messages


def build_repair_messages(previous: list[Message], bad_sql: str, error: str) -> list[Message]:
    """Relance le modèle avec le message d'erreur SQLite (auto-correction, 1 tour)."""
    return [
        *previous,
        Message("assistant", f"```sql\n{bad_sql}\n```"),
        Message(
            "user",
            f"Cette requête a échoué avec l'erreur : {error}\n"
            "Corrige-la. Réponds uniquement par la requête corrigée dans un bloc ```sql```.",
        ),
    ]
