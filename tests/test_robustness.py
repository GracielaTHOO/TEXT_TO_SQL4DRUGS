from __future__ import annotations

from pathlib import Path

import pytest

from medsql.eval.dataset import load_questions
from medsql.eval.robustness import robustness


def test_robustness_counts_the_four_outcomes() -> None:
    items = [
        {"id": "a", "correct": True},
        {"id": "b", "correct": True},
        {"id": "c", "correct": False},
        {"id": "a2", "correct": True, "paraphrase_de": "a"},
        {"id": "b2", "correct": False, "paraphrase_de": "b"},
        {"id": "c2", "correct": True, "paraphrase_de": "c"},
        {"id": "z2", "correct": True, "paraphrase_de": "absente"},  # source hors du run
    ]
    r = robustness(items)
    assert (r["pairs"], r["both"], r["only_original"], r["only_paraphrase"], r["neither"]) == (
        3,
        1,
        1,
        1,
        0,
    )
    assert r["consistency"] == pytest.approx(1 / 3)
    assert r["kept"] == pytest.approx(1 / 2)
    assert robustness([{"id": "a", "correct": True}]) == {}


def test_paraphrases_inherit_their_source() -> None:
    items = {q.id: q for q in load_questions()}
    paraphrases = [q for q in items.values() if q.paraphrase_de]
    assert len(paraphrases) == 30
    for q in paraphrases:
        source = items[q.paraphrase_de or ""]
        assert source.paraphrase_de is None
        assert (q.sql, q.difficulte, q.categorie, q.ordonne) == (
            source.sql,
            source.difficulte,
            source.categorie,
            source.ordonne,
        )
        assert q.question != source.question


@pytest.mark.parametrize(
    "extra",
    ["  paraphrase_de: q999\n", "  paraphrase_de: q001\n  sql: SELECT 1\n"],
)
def test_invalid_paraphrases_are_rejected(tmp_path: Path, extra: str) -> None:
    path = tmp_path / "q.yaml"
    path.write_text(
        "- id: q001\n  question: A ?\n  sql: SELECT 1\n  difficulte: facile\n  categorie: comptage\n"
        "- id: q002\n  question: B ?\n" + extra,
        "utf-8",
    )
    with pytest.raises(ValueError, match="q002"):
        load_questions(path)
