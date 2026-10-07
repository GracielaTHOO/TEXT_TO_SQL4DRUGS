from __future__ import annotations

from medsql.eval.metrics import soft_match, strict_match


def test_strict_order_insensitive_by_default() -> None:
    assert strict_match([(1,), (2,)], [(2,), (1,)])
    assert not strict_match([(1,), (2,)], [(2,), (1,)], ordered=True)


def test_numeric_normalization() -> None:
    assert strict_match([(37.123,)], [(37.1,)])
    assert strict_match([(3,)], [(3.0,)])
    assert not strict_match([(37.1,)], [(37.3,)])


def test_soft_accepts_extra_and_reordered_columns() -> None:
    gold = [("DOLIPRANE",), ("ADVIL",)]
    pred = [(1, "ADVIL"), (2, "DOLIPRANE")]
    assert soft_match(gold, pred)
    assert not strict_match(gold, pred)


def test_soft_rejects_missing_or_extra_rows() -> None:
    assert not soft_match([("A",), ("B",)], [("A",)])
    assert not soft_match([("A",)], [("A",), ("B",)])


def test_soft_rejects_fewer_columns() -> None:
    assert not soft_match([("A", 1)], [("A",)])


def test_soft_keeps_row_alignment() -> None:
    # Les colonnes ont les bonnes valeurs mais les paires sont mélangées.
    gold = [("A", 1), ("B", 2)]
    pred = [("A", 2), ("B", 1)]
    assert not soft_match(gold, pred)


def test_soft_ordered() -> None:
    gold = [("A",), ("B",)]
    assert soft_match(gold, [(10, "A"), (5, "B")], ordered=True)
    assert not soft_match(gold, [(10, "B"), (5, "A")], ordered=True)


def test_empty_results() -> None:
    assert soft_match([], [])
    assert not soft_match([], [("A",)])
