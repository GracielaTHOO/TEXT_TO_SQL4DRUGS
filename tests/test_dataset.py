from __future__ import annotations

import sqlite3

import pytest

from medsql.eval.dataset import load_questions
from medsql.prompting import FEW_SHOTS
from medsql.sql_guard import run_query, validate

QUESTIONS = load_questions()


def test_dataset_size_and_balance() -> None:
    assert len(QUESTIONS) >= 60
    levels = {q.difficulte for q in QUESTIONS}
    assert levels == {"facile", "moyen", "difficile"}


@pytest.mark.parametrize("item", QUESTIONS, ids=lambda q: q.id)
def test_gold_sql_is_safe_and_executes(item, conn: sqlite3.Connection) -> None:  # type: ignore[no-untyped-def]
    validate(item.sql)
    run_query(conn, item.sql, max_rows=None)


def test_ordered_questions_have_order_by() -> None:
    for q in QUESTIONS:
        if q.ordonne:
            assert "ORDER BY" in q.sql.upper(), q.id


def test_no_leakage_between_few_shots_and_eval() -> None:
    eval_questions = {q.question.lower() for q in QUESTIONS}
    for question, _ in FEW_SHOTS:
        assert question.lower() not in eval_questions
