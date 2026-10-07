"""Garde-fous d'exécution : le SQL généré par le LLM n'est jamais exécuté tel quel.

Trois barrières indépendantes (défense en profondeur) :

1. **Analyse syntaxique** (sqlglot) : une seule instruction, de type ``SELECT``/``WITH``,
   sans aucun nœud d'écriture ou d'administration.
2. **Connexion en lecture seule** : la base est ouverte en ``mode=ro``.
3. **Autorisateur SQLite** : toute opération autre que la lecture est refusée par le moteur,
   même si les deux barrières précédentes étaient contournées.

S'y ajoutent un délai maximal d'exécution et un plafond de lignes renvoyées.
"""

from __future__ import annotations

import re
import sqlite3
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

_FORBIDDEN_NODES: tuple[type[exp.Expression], ...] = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.Command,
    exp.Pragma,
    exp.Attach,
    exp.Detach,
)

_ALLOWED_ACTIONS = {
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_READ,
    sqlite3.SQLITE_FUNCTION,
    sqlite3.SQLITE_RECURSIVE,
}

_FENCE = re.compile(r"```(?:sql|sqlite)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


class UnsafeQueryError(ValueError):
    """La requête a été refusée par les garde-fous (SQL invalide ou interdit)."""


class ForbiddenQueryError(UnsafeQueryError):
    """La requête tente une opération interdite : elle n'est jamais « réparée »."""


@dataclass(frozen=True)
class QueryResult:
    columns: list[str]
    rows: list[tuple[object, ...]]
    truncated: bool
    duration_s: float


def extract_sql(text: str) -> str:
    """Extrait la requête d'une réponse de LLM (bloc ```sql``` ou texte brut)."""
    match = _FENCE.search(text)
    sql = match.group(1) if match else text
    sql = re.sub(r"^\s*(?:sql|requête)\s*:\s*", "", sql.strip(), flags=re.IGNORECASE)
    return sql.strip().rstrip(";").strip()


def validate(sql: str) -> str:
    """Vérifie qu'une requête est une lecture unique ; renvoie la requête normalisée."""
    if not sql.strip():
        raise UnsafeQueryError("Requête vide.")
    try:
        statements = [s for s in sqlglot.parse(sql, read="sqlite") if s is not None]
    except ParseError as exc:
        raise UnsafeQueryError(f"SQL invalide : {exc}") from exc
    if len(statements) != 1:
        raise ForbiddenQueryError("Une seule instruction SQL est autorisée.")
    tree = statements[0]
    if not isinstance(tree, exp.Query):
        raise ForbiddenQueryError("Seules les requêtes SELECT sont autorisées.")
    for node in tree.walk():
        if isinstance(node, _FORBIDDEN_NODES):
            raise ForbiddenQueryError(f"Opération interdite : {type(node).__name__}.")
    return sql.strip().rstrip(";")


def _authorizer(action: int, *_: object) -> int:
    return sqlite3.SQLITE_OK if action in _ALLOWED_ACTIONS else sqlite3.SQLITE_DENY


def sans_accents(value: object) -> str | None:
    """Fonction SQL ``sans_accents(x)`` : majuscules sans diacritiques.

    SQLite ne gère la casse que pour l'ASCII : ``'é' LIKE 'É'`` est faux. Cette fonction,
    exposée au LLM, rend les recherches textuelles robustes (``PARACÉTAMOL`` ≡ ``paracetamol``).
    """
    if value is None:
        return None
    decomposed = unicodedata.normalize("NFKD", str(value))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).upper()


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    """Ouvre la base en lecture seule, avec autorisateur et fonctions utilitaires."""
    if not db_path.exists():
        raise FileNotFoundError(f"Base introuvable : {db_path}. Lancez `medsql build`.")
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.create_function("sans_accents", 1, sans_accents, deterministic=True)
    conn.set_authorizer(_authorizer)
    return conn


def run_query(
    conn: sqlite3.Connection, sql: str, *, max_rows: int | None = 200, timeout_s: float = 10
) -> QueryResult:
    """Valide puis exécute une requête en lecture, avec délai et plafond de lignes."""
    safe_sql = validate(sql)
    deadline = time.monotonic() + timeout_s
    # Le gestionnaire de progression interrompt la requête si le délai est dépassé.
    conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 10_000)
    start = time.perf_counter()
    try:
        cursor = conn.execute(safe_sql)
        if max_rows is None:
            rows = cursor.fetchall()
            truncated = False
        else:
            rows = cursor.fetchmany(max_rows + 1)
            truncated = len(rows) > max_rows
            rows = rows[:max_rows]
    except sqlite3.OperationalError as exc:
        if "interrupted" in str(exc):
            raise TimeoutError(f"Requête interrompue après {timeout_s:g} s.") from exc
        raise
    finally:
        conn.set_progress_handler(None, 0)
    columns = [d[0] for d in cursor.description or ()]
    return QueryResult(columns, [tuple(r) for r in rows], truncated, time.perf_counter() - start)
