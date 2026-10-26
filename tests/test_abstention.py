from __future__ import annotations

from pathlib import Path

import pytest

from medsql.eval.abstention import abstention_stats, answerable
from medsql.eval.dataset import load_questions
from medsql.eval.significance import mcnemar, run_ci


def _item(qid: str, correct: bool, *, outside: bool = False, abstained: bool = False) -> dict:  # type: ignore[type-arg]
    return {"id": qid, "correct": correct, "hors_perimetre": outside, "abstained": abstained}


def test_old_runs_have_no_abstention() -> None:
    items = [{"id": "q1", "correct": True}]
    assert abstention_stats(items) == {}
    assert answerable(items) == items


def test_abstention_stats() -> None:
    items = [
        _item("q1", True),
        _item("q2", False, abstained=True),
        _item("o1", True, outside=True, abstained=True),
        _item("o2", False, outside=True),
    ]
    stats = abstention_stats(items)
    assert stats["out_of_scope"] == 2
    assert stats["correct"] == 1
    assert stats["rate"] == 0.5
    assert stats["false_abstentions"] == 1
    assert stats["false_rate"] == 0.5


def test_statistics_ignore_out_of_scope_questions() -> None:
    a = [_item("q1", True), _item("o1", True, outside=True, abstained=True)]
    b = [_item("q1", True), _item("o1", False, outside=True)]
    assert mcnemar(a, b).n == 1
    assert run_ci(b) == (1.0, 1.0)


def test_dataset_has_ten_out_of_scope_questions() -> None:
    items = load_questions()
    outside = [q for q in items if q.hors_perimetre]
    assert len(outside) == 10
    assert all(q.sql == "" and q.categorie == "hors_perimetre" for q in outside)
    assert all(q.sql for q in items if not q.hors_perimetre)


@pytest.mark.parametrize(
    "entry",
    [
        "  hors_perimetre: true\n  sql: SELECT 1\n",
        "  hors_perimetre: true\n  categorie: comptage\n",
        "  categorie: hors_perimetre\n  sql: SELECT 1\n",
    ],
)
def test_loader_rejects_inconsistent_out_of_scope_entries(tmp_path: Path, entry: str) -> None:
    path = tmp_path / "q.yaml"
    path.write_text(f"- id: x\n  question: Q ?\n  difficulte: facile\n{entry}", "utf-8")
    with pytest.raises(ValueError):
        load_questions(path)


def test_out_of_scope_question_cannot_be_paraphrased(tmp_path: Path) -> None:
    path = tmp_path / "q.yaml"
    path.write_text(
        "- id: o\n  question: Météo ?\n  difficulte: facile\n  hors_perimetre: true\n"
        "- id: p\n  question: Et la météo ?\n  paraphrase_de: o\n",
        "utf-8",
    )
    with pytest.raises(ValueError, match="source de reformulation invalide"):
        load_questions(path)
