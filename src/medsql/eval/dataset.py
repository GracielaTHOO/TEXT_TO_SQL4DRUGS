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
    paraphrase_de: str | None = None  # identifiant de la question reformulée


def default_path() -> Path:
    return Path(str(resources.files("medsql.eval").joinpath("questions.yaml")))


def load_questions(path: Path | None = None) -> list[EvalItem]:
    """Charge et valide le jeu (identifiants uniques, valeurs d'énumération connues).

    Une reformulation (``paraphrase_de``) hérite de la requête de référence, de la difficulté,
    de la catégorie et de l'ordre de sa question source : seule la formulation change.
    """
    raw = yaml.safe_load((path or default_path()).read_text("utf-8"))
    by_id = {str(r["id"]): r for r in raw}
    if len(by_id) != len(raw):
        raise ValueError("Identifiants de questions dupliqués.")
    items = []
    for r in raw:
        source_id = r.get("paraphrase_de")
        source = r
        if source_id is not None:
            source = by_id.get(str(source_id), {})
            if not source or "paraphrase_de" in source:
                raise ValueError(f"{r['id']} : source de reformulation invalide {source_id!r}")
            if any(k in r for k in ("sql", "difficulte", "categorie", "ordonne")):
                raise ValueError(
                    f"{r['id']} : une reformulation n'a que id, question, paraphrase_de"
                )
        items.append(
            EvalItem(
                id=str(r["id"]),
                question=str(r["question"]).strip(),
                sql=str(source["sql"]).strip(),
                difficulte=str(source["difficulte"]),
                categorie=str(source["categorie"]),
                ordonne=bool(source.get("ordonne", False)),
                paraphrase_de=None if source_id is None else str(source_id),
            )
        )
    for item in items:
        if item.difficulte not in DIFFICULTIES:
            raise ValueError(f"{item.id} : difficulté inconnue {item.difficulte!r}")
        if item.categorie not in CATEGORIES:
            raise ValueError(f"{item.id} : catégorie inconnue {item.categorie!r}")
    return items
