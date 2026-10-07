"""Chargement et validation du jeu de questions."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import yaml

DIFFICULTIES = ("facile", "moyen", "difficile")
CATEGORIES = (
    "comptage",
    "filtrage",
    "jointure",
    "agregation",
    "classement",
    "dates",
    "prix",
    "generiques",
    "has",
    "disponibilite",
)


@dataclass(frozen=True)
class EvalItem:
    id: str
    question: str
    sql: str
    difficulte: str
    categorie: str
    ordonne: bool = False


def default_path() -> Path:
    return Path(str(resources.files("medsql.eval").joinpath("questions.yaml")))


def load_questions(path: Path | None = None) -> list[EvalItem]:
    """Charge et valide le jeu (identifiants uniques, valeurs d'énumération connues)."""
    raw = yaml.safe_load((path or default_path()).read_text("utf-8"))
    items = [
        EvalItem(
            id=str(r["id"]),
            question=str(r["question"]).strip(),
            sql=str(r["sql"]).strip(),
            difficulte=str(r["difficulte"]),
            categorie=str(r["categorie"]),
            ordonne=bool(r.get("ordonne", False)),
        )
        for r in raw
    ]
    ids = [i.id for i in items]
    if len(ids) != len(set(ids)):
        raise ValueError("Identifiants de questions dupliqués.")
    for item in items:
        if item.difficulte not in DIFFICULTIES:
            raise ValueError(f"{item.id} : difficulté inconnue {item.difficulte!r}")
        if item.categorie not in CATEGORIES:
            raise ValueError(f"{item.id} : catégorie inconnue {item.categorie!r}")
    return items
