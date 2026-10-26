from __future__ import annotations

from typing import Any

import pytest

from medsql.eval.errors import ERROR_LABELS, classify, error_breakdown, sql_shape

GOLD = (
    "SELECT COUNT(DISTINCT m.cis) FROM medicaments m JOIN compositions c ON c.cis = m.cis "
    "WHERE sans_accents(c.substance) LIKE '%PARACETAMOL%'"
)


def _item(pred: str | None, **extra: Any) -> dict[str, Any]:
    base = {
        "id": "q",
        "gold_sql": GOLD,
        "pred_sql": pred,
        "correct": False,
        "executable": pred is not None,
        "error": None,
        "gold_rows": 1,
        "pred_rows": 1,
    }
    return base | extra


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        (_item(GOLD, correct=True), None),
        (_item(None, error="LLMError: ReadTimeout: délai"), "erreur_llm"),
        (_item("SELEC x", executable=False, error="UnsafeQueryError"), "sql_invalide"),
        (
            _item("SELECT COUNT(*) FROM medicaments WHERE denomination LIKE '%DOLI%'"),
            "table_manquante",
        ),
        (
            _item(
                GOLD.replace("ON c.cis = m.cis", "ON c.cis = m.cis JOIN mitm t ON t.cis = m.cis")
            ),
            "jointure",
        ),
        (_item(GOLD.replace("COUNT(DISTINCT m.cis)", "COUNT(*)")), "agregat"),
        (_item(GOLD.replace("PARACETAMOL", "IBUPROFENE")), "filtre_texte"),
        (_item(GOLD.replace("'%PARACETAMOL%'", "'%paracétamol%'")), "valeurs"),
        (_item(GOLD, gold_rows=3, pred_rows=5), "lignes_en_trop"),
        (_item(GOLD, gold_rows=3, pred_rows=1), "lignes_manquantes"),
    ],
)
def test_classify(item: dict[str, Any], expected: str | None) -> None:
    assert classify(item) == expected


def test_shape_ignores_cte_names_and_folds_text() -> None:
    shape = sql_shape("WITH x AS (SELECT cis FROM mitm) SELECT * FROM x WHERE a = 'Été%'")
    assert shape is not None
    assert shape.tables == frozenset({"mitm"})
    assert shape.literals == frozenset({"ETE"})
    assert sql_shape("SELECT 'non fermé") is None


def test_breakdown_groups_ids_in_display_order() -> None:
    items = [
        _item(GOLD.replace("PARACETAMOL", "IBUPROFENE"), id="q2"),
        _item(None, id="q1", error="LLMError: x"),
        _item(GOLD, id="q3", correct=True),
    ]
    assert error_breakdown(items) == {"erreur_llm": ["q1"], "filtre_texte": ["q2"]}
    assert set(ERROR_LABELS) >= set(error_breakdown(items))


def test_abstention_causes_come_first() -> None:
    assert classify(_item("SELECT 1", hors_perimetre=True, gold_sql="")) == "abstention_manquee"
    assert classify(_item(None, abstained=True)) == "abstention_a_tort"
    assert classify(_item(None, hors_perimetre=True, abstained=True, correct=True)) is None
    assert {"abstention_manquee", "abstention_a_tort"} <= ERROR_LABELS.keys()
