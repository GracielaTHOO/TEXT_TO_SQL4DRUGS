"""Réponse rédigée en français, export CSV et historique pour la démo (S11).

La phrase de réponse est construite **à partir du résultat exécuté**, par gabarits, et non
rédigée par le LLM : elle ne peut donc pas affirmer un chiffre que la base n'a pas renvoyé,
et elle ne coûte aucun appel de plus. Elle dit ce que montre le tableau (une valeur, une
ligne, ou le nombre de lignes et les premières) ; le tableau reste la réponse complète.
"""

from __future__ import annotations

import csv
import io
from collections import deque
from dataclasses import dataclass
from datetime import datetime

from medsql.pipeline import OUT_OF_SCOPE_MESSAGE, Answer
from medsql.sql_guard import QueryResult

PREVIEW = 3  # nombre de lignes citées dans la phrase
HISTORY_SIZE = 20
NBSP = " "  # espace fine insécable, séparateur de milliers en français


def _format_float(value: float) -> str:
    if value.is_integer() and abs(value) < 1e15:
        return format_value(int(value))
    if abs(value) < 0.01:  # 0,004 ne doit pas s'afficher « 0 »
        return f"{value:.2g}".replace(".", ",")
    text = f"{value:,.2f}".rstrip("0").rstrip(".")
    return text.replace(",", NBSP).replace(".", ",")


def format_value(value: object) -> str:
    """Valeur affichée à la française : 13 650, 37,5, « vide » pour NULL."""
    if value is None:
        return "vide"
    if isinstance(value, bool):
        return "oui" if value else "non"
    if isinstance(value, int):
        return f"{value:,}".replace(",", NBSP)
    if isinstance(value, float):
        return _format_float(value)
    return str(value)


def _label(column: str) -> str:
    return column.replace("_", " ")


def _row_text(columns: list[str], row: tuple[object, ...]) -> str:
    if len(row) == 1:
        return format_value(row[0])
    return ", ".join(f"{_label(c)} : {format_value(v)}" for c, v in zip(columns, row, strict=True))


def _key_column(result: QueryResult) -> int:
    """Colonne qui nomme les lignes : la première colonne de texte, sinon la première."""
    for j in range(len(result.columns)):
        if all(isinstance(row[j], str) for row in result.rows[:PREVIEW]):
            return j
    return 0


def describe(result: QueryResult) -> str:
    """Phrase qui résume un résultat d'exécution."""
    n = len(result.rows)
    if n == 0:
        return "Aucun résultat : la base ne contient aucune ligne qui réponde à cette question."
    if n == 1 and len(result.columns) == 1:
        return f"Réponse : **{format_value(result.rows[0][0])}** ({_label(result.columns[0])})."
    if n == 1:
        return f"Un résultat : {_row_text(result.columns, result.rows[0])}."
    count = f"au moins {format_value(n)}" if result.truncated else format_value(n)
    key = _key_column(result)
    shown = " ; ".join(format_value(row[key]) for row in result.rows[:PREVIEW])
    more = ", entre autres" if n > PREVIEW else ""
    truncated = " Affichage limité : la liste complète est plus longue." if result.truncated else ""
    return f"**{count}** résultats{more} : {shown}.{truncated}"


def narrate(answer: Answer) -> str:
    """Réponse rédigée pour une question posée à la démo ou à la CLI."""
    if answer.abstained:
        return OUT_OF_SCOPE_MESSAGE
    if answer.error or answer.result is None:
        return (
            "La question n'a pas pu être traduite en une requête valide. Essayez de la reformuler."
        )
    return describe(answer.result)


def to_csv(result: QueryResult) -> str:
    """CSV à la française (séparateur « ; », virgule décimale), lisible tel quel par un tableur.

    Le fichier est écrit en UTF-8 avec BOM par l'appelant (``encoding="utf-8-sig"``).
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")
    writer.writerow(result.columns)
    for row in result.rows:
        writer.writerow(
            [
                "" if v is None else str(v).replace(".", ",") if isinstance(v, float) else v
                for v in row
            ]
        )
    return buffer.getvalue()


@dataclass(frozen=True)
class HistoryEntry:
    time: str
    question: str
    outcome: str
    rows: int | None
    seconds: float


class History:
    """Dernières questions posées dans une session de la démo, la plus récente en tête."""

    COLUMNS = ("Heure", "Question", "Issue", "Lignes", "Durée (s)")

    def __init__(self, size: int = HISTORY_SIZE) -> None:
        self._entries: deque[HistoryEntry] = deque(maxlen=size)

    def add(self, answer: Answer, *, now: datetime | None = None) -> None:
        if answer.abstained:
            outcome, rows = "hors périmètre", None
        elif answer.error or answer.result is None:
            outcome, rows = "erreur", None
        else:
            outcome, rows = "réponse", len(answer.result.rows)
        self._entries.appendleft(
            HistoryEntry(
                (now or datetime.now()).strftime("%H:%M:%S"),
                answer.question,
                outcome,
                rows,
                round(answer.total_latency_s, 1),
            )
        )

    def rows(self) -> list[list[object]]:
        return [[e.time, e.question, e.outcome, e.rows, e.seconds] for e in self._entries]

    def __len__(self) -> int:
        return len(self._entries)
