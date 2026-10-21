from __future__ import annotations

import pytest

from medsql.eval.significance import bootstrap_ci, mcnemar


def _items(pattern: str) -> list[dict[str, object]]:
    return [{"id": f"q{i}", "correct": c == "1"} for i, c in enumerate(pattern)]


def test_bootstrap_ci_brackets_the_mean_and_is_reproducible() -> None:
    outcomes = [True] * 36 + [False] * 24  # 60 %
    lo, hi = bootstrap_ci(outcomes)
    assert lo < 0.6 < hi
    # Ordre de grandeur attendu pour n = 60 : environ ±12 points.
    assert 0.18 < hi - lo < 0.30
    assert bootstrap_ci(outcomes) == (lo, hi)


def test_bootstrap_ci_degenerate_cases() -> None:
    assert bootstrap_ci([]) == (0.0, 0.0)
    assert bootstrap_ci([True] * 10) == (1.0, 1.0)


def test_mcnemar_counts_discordant_pairs_only() -> None:
    a = _items("1111000011")
    b = _items("1100000011")
    result = mcnemar(a, b)
    assert (result.n, result.only_a, result.only_b) == (10, 2, 0)
    assert result.p_value == pytest.approx(0.5)  # 2 × (1/2)²
    assert not result.significant


def test_mcnemar_exact_p_value_and_symmetry() -> None:
    a = _items("1" * 10 + "0" * 10)
    b = _items("0" * 10 + "0" * 10)
    result = mcnemar(a, b)
    assert result.p_value == pytest.approx(2 / 2**10)
    assert result.significant
    assert mcnemar(b, a).p_value == result.p_value


def test_mcnemar_pairs_by_question_id() -> None:
    a = [{"id": "q1", "correct": True}, {"id": "q2", "correct": True}]
    b = [{"id": "q2", "correct": False}, {"id": "q3", "correct": True}]
    result = mcnemar(a, b)
    assert (result.n, result.only_a, result.only_b) == (1, 1, 0)
    assert mcnemar([], []).p_value == 1.0
