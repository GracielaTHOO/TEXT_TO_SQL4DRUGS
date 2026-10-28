from __future__ import annotations

import sqlite3
from dataclasses import asdict
from pathlib import Path

from medsql.eval.dataset import load_questions
from medsql.eval.runner import evaluate_item, load_runs, save_run, summarize
from medsql.pipeline import Text2SQL
from medsql.report import (
    MAX_ALL_PAIRS,
    README_END,
    README_START,
    ablations,
    pairwise,
    render_dashboard,
    update_readme,
)
from tests.conftest import OracleLLM


def _make_run(conn: sqlite3.Connection, out: Path) -> None:
    engine = Text2SQL(OracleLLM(), conn, max_rows=10_000)
    results = [evaluate_item(engine, conn, item) for item in load_questions()[:5]]
    summary = summarize(
        results, model="oracle", backend="test", config={"few_shot": True, "value_hints": True}
    )
    save_run(summary, results, out)
    assert asdict(summary)["n"] == 5


def test_dashboard_and_readme(conn: sqlite3.Connection, tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    _make_run(conn, runs_dir)
    runs = load_runs(runs_dir)
    page = render_dashboard(runs, [("Spécialités", "22")])
    assert "<svg" in page
    assert "100,0 %" in page
    readme = tmp_path / "README.md"
    readme.write_text(f"intro\n{README_START}\nvieux\n{README_END}\nfin\n", "utf-8")
    assert update_readme(readme, runs)
    text = readme.read_text("utf-8")
    assert "| oracle | **100,0 %**" in text
    assert "vieux" not in text


def test_dashboard_without_runs() -> None:
    assert "Aucun run" in render_dashboard([])


def _summary(model: str, accuracy: float, **config: object) -> dict[str, object]:
    return {"model": model, "accuracy": accuracy, "config": config}


def test_ablations_compare_variants_to_the_model_baseline() -> None:
    board = [
        {
            "items": [],
            "summary": _summary("m", 0.50, few_shot=True, max_repairs=1),
        },  # run ancien, sans clé
        {
            "items": [],
            "summary": _summary("m", 0.60, few_shot=True, max_repairs=1, value_hints=True),
        },
        {
            "items": [],
            "summary": _summary("m", 0.40, few_shot=False, max_repairs=1, value_hints=True),
        },
        {"items": [], "summary": _summary("seul", 0.30, few_shot=False)},  # pas de base : ignoré
    ]
    rows = ablations(board)  # type: ignore[arg-type]
    # zero-shot n'est comparé qu'au run qui ne diffère que par les exemples (ici, la base).
    assert [(r[1], r[2], round(r[4], 1)) for r in rows] == [
        ("sans libellés exacts", "base", -10.0),
        ("zero-shot", "base", -20.0),
    ]


def test_ablations_compare_runs_differing_by_one_factor_only() -> None:
    board = [
        {"items": [], "summary": _summary("m", 0.50, few_shot=True, max_repairs=1)},
        {"items": [], "summary": _summary("m", 0.40, few_shot=False, max_repairs=1)},
    ]
    rows = ablations(board)  # type: ignore[arg-type]
    assert [(r[1], r[2], round(r[4], 1)) for r in rows] == [
        ("zero-shot", "sans libellés exacts", -10.0)
    ]


def test_dashboard_and_readme_show_abstention(conn: sqlite3.Connection, tmp_path: Path) -> None:
    items = load_questions()
    chosen = items[:3] + [q for q in items if q.hors_perimetre][:2]
    engine = Text2SQL(OracleLLM(), conn, max_rows=10_000)
    results = [evaluate_item(engine, conn, item) for item in chosen]
    summary = summarize(results, model="oracle", backend="test", config={"value_hints": True})
    save_run(summary, results, tmp_path)
    runs = load_runs(tmp_path)
    page = render_dashboard(runs)
    assert "Savoir s'abstenir" in page
    assert "abstention attendue" in page
    readme = tmp_path / "README.md"
    readme.write_text(f"{README_START}\n{README_END}\n", "utf-8")
    update_readme(readme, runs)
    text = readme.read_text("utf-8")
    assert "| 2/2 |" in text
    assert "_3 questions + 2 hors périmètre" in text


def _board_run(model: str, outcomes: list[bool]) -> dict[str, object]:
    summary = {
        "model": model,
        "backend": "ollama",
        "accuracy": sum(outcomes) / len(outcomes),
        "accuracy_strict": 0.0,
        "executable_rate": 1.0,
        "repaired": 0,
        "latency_p50_s": 1.0,
        "latency_p95_s": 2.0,
        "tokens_per_question": 100.0,
        "created_at": "2026-10-28T08:00:00+00:00",
        "n": len(outcomes),
        "by_difficulty": {},
        "by_category": {},
        "config": {"few_shot": True, "max_repairs": 1, "value_hints": True},
    }
    items = [
        {
            "id": f"q{i}",
            "question": "Combien ?",
            "difficulte": "facile",
            "gold_sql": "SELECT COUNT(*) FROM medicaments",
            "pred_sql": "SELECT COUNT(*) FROM medicaments",
            "correct": c,
            "executable": True,
            "error": None,
            "gold_rows": 1,
            "pred_rows": 1,
            "total_latency_s": 1.0,
        }
        for i, c in enumerate(outcomes)
    ]
    return {"summary": summary, "items": items}


def test_pairwise_compares_all_pairs_then_only_to_the_best() -> None:
    runs = [_board_run(f"m{k}", [True] * (9 - k) + [False] * k) for k in range(6)]
    assert len(pairwise(runs[:MAX_ALL_PAIRS])) == MAX_ALL_PAIRS * (MAX_ALL_PAIRS - 1) // 2
    many = pairwise(runs)
    assert len(many) == 5
    assert all(a == "m0" for a, _, _ in many)


def test_families_table_lists_catalogued_models() -> None:
    runs = [
        _board_run("qwen2.5-coder:7b", [True, True, False]),
        _board_run("llama3.1:8b", [True, False, False]),
        _board_run("sqlcoder:7b", [False, False, False]),
    ]
    page = render_dashboard(runs)
    assert "Familles de modèles" in page
    assert "Meta" in page and "Defog" in page and "généraliste" in page


def test_families_table_needs_two_catalogued_models() -> None:
    runs = [_board_run("qwen2.5-coder:7b", [True]), _board_run("inconnu:1b", [False])]
    assert "Familles de modèles" not in render_dashboard(runs)
