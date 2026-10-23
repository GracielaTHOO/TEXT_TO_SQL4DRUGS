from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import medsql.llm
from medsql.cli import app
from tests.conftest import FIXTURES, OracleLLM, ScriptedLLM

runner = CliRunner()


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("MEDSQL_DATA_DIR", str(tmp_path / "data"))
    result = runner.invoke(app, ["build", "--raw-dir", str(FIXTURES)])
    assert result.exit_code == 0, result.output
    return tmp_path / "data"


def test_build_and_stats(data_dir: Path) -> None:
    assert (data_dir / "bdpm.sqlite").exists()
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "Spécialités commercialisées" in result.output


def test_ask(data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    llm = ScriptedLLM("```sql\nSELECT COUNT(*) AS n FROM medicaments\n```")
    monkeypatch.setattr(medsql.llm, "make_client", lambda _s: llm)
    result = runner.invoke(app, ["ask", "Combien de médicaments ?"])
    assert result.exit_code == 0, result.output
    assert "22" in result.output


def test_ask_reports_errors(data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        medsql.llm, "make_client", lambda _s: ScriptedLLM("DELETE FROM medicaments")
    )
    result = runner.invoke(app, ["ask", "Supprime tout"])
    assert result.exit_code == 1


def test_eval_and_report(data_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(medsql.llm, "make_client", lambda _s: OracleLLM())
    runs = tmp_path / "runs"
    result = runner.invoke(app, ["eval", "--model", "oracle", "--out", str(runs)])
    assert result.exit_code == 0, result.output
    assert "Exactitude : 100.0 %" in result.output
    readme = tmp_path / "README.md"
    readme.write_text("<!-- RESULTS:START -->\n<!-- RESULTS:END -->\n", "utf-8")
    out = tmp_path / "dashboard.html"
    result = runner.invoke(
        app, ["report", "--runs-dir", str(runs), "--out", str(out), "--readme", str(readme)]
    )
    assert result.exit_code == 0, result.output
    assert "Spécialités commercialisées" in out.read_text("utf-8")
    assert "**100,0 %**" in readme.read_text("utf-8")


def test_docs(tmp_path: Path) -> None:
    out = tmp_path / "data.md"
    assert runner.invoke(app, ["docs", "--out", str(out)]).exit_code == 0
    assert "## `medicaments`" in out.read_text("utf-8")


def test_profile_and_check_questions(data_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "profil.md"
    result = runner.invoke(app, ["profile", "--out", str(out)])
    assert result.exit_code == 0, result.output
    text = out.read_text("utf-8")
    assert "| `medicaments` | 22 |" in text
    assert "Commercialisée" in text
    report = tmp_path / "check.json"
    result = runner.invoke(app, ["check-questions", "--out", str(report)])
    assert result.exit_code == 0, result.output
    data = json.loads(report.read_text("utf-8"))
    assert len(data["questions"]) == 90
    # Sur l'échantillon synthétique, quelques références sont vides : elles sont signalées.
    assert "q024" in data["to_review"]
