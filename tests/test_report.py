from __future__ import annotations

import sqlite3
from dataclasses import asdict
from pathlib import Path

from medsql.eval.dataset import load_questions
from medsql.eval.runner import evaluate_item, load_runs, save_run, summarize
from medsql.pipeline import Text2SQL
from medsql.report import (
    README_END,
    README_START,
    ablations,
    render_dashboard,
    update_readme,
)
from tests.conftest import OracleLLM


def _make_run(conn: sqlite3.Connection, out: Path) -> None:
    engine = Text2SQL(OracleLLM(), conn, max_rows=10_000)
    results = [evaluate_item(engine, conn, item) for item in load_questions()[:5]]
    summary = summarize(results, model="oracle", backend="test", config={"few_shot": True})
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
        {"summary": _summary("m", 0.50, few_shot=True, max_repairs=1)},
        {"summary": _summary("m", 0.60, few_shot=True, max_repairs=1, value_hints=True)},
        {"summary": _summary("m", 0.40, few_shot=False, max_repairs=1)},
        {"summary": _summary("seul", 0.30, few_shot=False)},  # pas de base : ignoré
    ]
    rows = ablations(board)  # type: ignore[arg-type]
    assert [(r[1], round(r[3], 1)) for r in rows] == [
        ("libellés exacts", 10.0),
        ("zero-shot", -10.0),
    ]
