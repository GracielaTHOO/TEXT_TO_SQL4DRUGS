from __future__ import annotations

import sqlite3

from medsql.eval.dataset import EvalItem
from medsql.profile import check_questions


def _item(qid: str, sql: str) -> EvalItem:
    return EvalItem(id=qid, question="?", sql=sql, difficulte="facile", categorie="comptage")


def test_check_questions_flags_empty_degenerate_and_broken(conn: sqlite3.Connection) -> None:
    items = [
        _item("ok", "SELECT COUNT(*) FROM medicaments"),
        _item("vide", "SELECT cis FROM medicaments WHERE 0"),
        _item("zero", "SELECT COUNT(*) FROM informations_importantes WHERE 0"),
        _item("null", "SELECT MAX(date_fin) FROM informations_importantes WHERE 0"),
        _item("casse", "SELECT colonne_inconnue FROM medicaments"),
    ]
    checks = {c.id: c for c in check_questions(conn, items)}
    assert not checks["ok"].needs_review
    assert checks["vide"].rows == 0 and checks["vide"].needs_review
    assert checks["zero"].degenerate and checks["zero"].needs_review
    assert checks["null"].degenerate
    assert checks["casse"].error is not None and checks["casse"].needs_review
