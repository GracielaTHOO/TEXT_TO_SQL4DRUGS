"""Profil de la base réelle : volumétrie, complétude, valeurs fréquentes, plages de dates.

Produit ``docs/donnees-profil.md`` (commande ``medsql profile``), régénéré par le workflow
d'évaluation à chaque téléchargement de la BDPM. Sert aussi à vérifier le jeu de questions
sur les vraies données (``medsql check-questions``).
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from medsql.data.schema import TABLES
from medsql.eval.dataset import EvalItem
from medsql.sql_guard import run_query

# Colonnes catégorielles dont on publie les valeurs les plus fréquentes.
CATEGORICAL: tuple[tuple[str, str], ...] = (
    ("medicaments", "etat_commercialisation"),
    ("medicaments", "statut_amm"),
    ("medicaments", "type_procedure_amm"),
    ("medicaments", "statut_bdm"),
    ("medicaments", "forme_pharmaceutique"),
    ("medicament_voies", "voie"),
    ("presentations", "taux_remboursement"),
    ("presentations", "statut_administratif"),
    ("compositions", "nature_composant"),
    ("groupes_generiques", "type_libelle"),
    ("avis_smr", "valeur_smr"),
    ("avis_asmr", "valeur_asmr"),
    ("conditions_prescription", "condition"),
    ("disponibilites", "statut"),
)
TOP_N = 8


def _md_escape(value: object) -> str:
    text = "NULL" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")[:80]


def _fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def profile_markdown(conn: sqlite3.Connection, *, downloaded_at: str | None = None) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Profil des données",
        "",
        "> Fichier généré par `medsql profile` sur la base réelle. Ne pas éditer à la main.",
        "",
        f"Généré le {now}" + (f", BDPM téléchargée le {downloaded_at}." if downloaded_at else "."),
        "",
        "## Volumétrie et complétude",
        "",
        "| Table | Lignes | Colonnes avec valeurs manquantes (part de NULL) |",
        "|---|---:|---|",
    ]
    for table in TABLES:
        total = conn.execute(f"SELECT COUNT(*) FROM {table.name}").fetchone()[0]
        gaps = []
        if total:
            for col in table.columns:
                nulls = conn.execute(
                    f"SELECT COUNT(*) FROM {table.name} WHERE {col.name} IS NULL"
                ).fetchone()[0]
                if nulls:
                    gaps.append(f"`{col.name}` {100 * nulls / total:.0f} %")
        lines.append(f"| `{table.name}` | {_fmt_int(total)} | {', '.join(gaps) or '—'} |")

    lines += ["", "## Plages de dates", "", "| Colonne | Min | Max |", "|---|---|---|"]
    for table in TABLES:
        for col in table.columns:
            if col.sql_type == "DATE":
                lo, hi = conn.execute(
                    f"SELECT MIN({col.name}), MAX({col.name}) FROM {table.name}"
                ).fetchone()
                lines.append(f"| `{table.name}.{col.name}` | {lo or '—'} | {hi or '—'} |")

    lines += ["", "## Valeurs les plus fréquentes", ""]
    for table_name, col_name in CATEGORICAL:
        distinct = conn.execute(f"SELECT COUNT(DISTINCT {col_name}) FROM {table_name}").fetchone()[
            0
        ]
        rows = conn.execute(
            f"SELECT {col_name}, COUNT(*) AS n FROM {table_name} "
            f"GROUP BY {col_name} ORDER BY n DESC LIMIT {TOP_N}"
        ).fetchall()
        lines += [
            f"### `{table_name}.{col_name}` ({_fmt_int(distinct)} valeurs distinctes)",
            "",
            "| Valeur | Lignes |",
            "|---|---:|",
        ]
        lines += [f"| {_md_escape(v)} | {_fmt_int(n)} |" for v, n in rows]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


@dataclass(frozen=True)
class QuestionCheck:
    id: str
    rows: int | None
    seconds: float
    error: str | None
    degenerate: bool = False  # une seule valeur, nulle ou NULL (ex. COUNT sur une table vide)

    @property
    def needs_review(self) -> bool:
        return self.error is not None or self.rows == 0 or self.degenerate


def check_questions(conn: sqlite3.Connection, items: list[EvalItem]) -> list[QuestionCheck]:
    """Exécute chaque requête de référence sur la base et signale celles à revoir."""
    checks = []
    for item in items:
        start = time.perf_counter()
        rows: int | None = None
        error: str | None = None
        try:
            rows = len(run_query(conn, item.sql, max_rows=10_000, timeout_s=60).rows)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        checks.append(QuestionCheck(item.id, rows, round(time.perf_counter() - start, 3), error))
    return checks


def checks_as_dict(checks: list[QuestionCheck]) -> dict[str, object]:
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "to_review": [c.id for c in checks if c.needs_review],
        "questions": [asdict(c) for c in checks],
    }
