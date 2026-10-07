"""Chiffres clés de la base, utilisés par la CLI, la démo et le tableau de bord."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class KeyFigure:
    key: str
    label: str
    sql: str
    unit: str = ""


KEY_FIGURES: tuple[KeyFigure, ...] = (
    KeyFigure("specialites", "Spécialités (codes CIS)", "SELECT COUNT(*) FROM medicaments"),
    KeyFigure(
        "commercialisees",
        "Spécialités commercialisées",
        "SELECT COUNT(*) FROM medicaments WHERE etat_commercialisation = 'Commercialisée'",
    ),
    KeyFigure(
        "presentations", "Présentations (boîtes CIP13)", "SELECT COUNT(*) FROM presentations"
    ),
    KeyFigure(
        "remboursees_pct",
        "Présentations remboursées",
        "SELECT ROUND(100.0 * SUM(taux_remboursement IS NOT NULL) / COUNT(*), 1) FROM presentations",
        "%",
    ),
    KeyFigure(
        "substances",
        "Substances actives distinctes",
        "SELECT COUNT(DISTINCT code_substance) FROM compositions WHERE nature_composant = 'SA'",
    ),
    KeyFigure(
        "titulaires", "Titulaires d'AMM", "SELECT COUNT(DISTINCT titulaires) FROM medicaments"
    ),
    KeyFigure(
        "groupes_generiques",
        "Groupes génériques",
        "SELECT COUNT(DISTINCT id_groupe) FROM groupes_generiques",
    ),
    KeyFigure(
        "ruptures",
        "Spécialités en rupture ou tension",
        "SELECT COUNT(DISTINCT cis) FROM disponibilites WHERE code_statut IN (1, 2)",
    ),
    KeyFigure(
        "mitm", "Médicaments d'intérêt thérapeutique majeur", "SELECT COUNT(DISTINCT cis) FROM mitm"
    ),
    KeyFigure(
        "avis_has",
        "Avis HAS (SMR + ASMR)",
        "SELECT (SELECT COUNT(*) FROM avis_smr) + (SELECT COUNT(*) FROM avis_asmr)",
    ),
)


def key_figures(conn: sqlite3.Connection) -> list[tuple[KeyFigure, float | int | None]]:
    return [(kf, conn.execute(kf.sql).fetchone()[0]) for kf in KEY_FIGURES]


def table_sizes(conn: sqlite3.Connection) -> dict[str, int]:
    names = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    return {n: conn.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0] for n in names}
