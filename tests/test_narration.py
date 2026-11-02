from __future__ import annotations

import csv
import importlib.util
import io
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType

import pytest

from medsql.narration import NBSP, History, describe, format_value, narrate, to_csv
from medsql.pipeline import OUT_OF_SCOPE_MESSAGE, Answer, Text2SQL
from medsql.sql_guard import QueryResult
from tests.conftest import ScriptedLLM


def _result(columns: list[str], rows: list[tuple[object, ...]], truncated: bool = False):  # type: ignore[no-untyped-def]
    return QueryResult(columns, rows, truncated, 0.01)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (13650, f"13{NBSP}650"),
        (37.5, "37,5"),
        (1234.567, f"1{NBSP}234,57"),
        (12.0, "12"),
        (0.004, "0,004"),
        (None, "vide"),
        ("DOLIPRANE", "DOLIPRANE"),
    ],
)
def test_values_are_written_the_french_way(value: object, expected: str) -> None:
    assert format_value(value) == expected


def test_single_value_answer() -> None:
    text = describe(_result(["nb_specialites"], [(13650,)]))
    assert text == f"Réponse : **13{NBSP}650** (nb specialites)."


def test_single_row_answer_names_each_column() -> None:
    text = describe(_result(["denomination", "prix"], [("DOLIPRANE 1000 mg", 2.18)]))
    assert text == "Un résultat : denomination : DOLIPRANE 1000 mg, prix : 2,18."


def test_list_answer_counts_and_previews_three_rows() -> None:
    rows = [(f"M{i}",) for i in range(5)]
    text = describe(_result(["denomination"], rows))
    assert text == "**5** résultats, entre autres : M0 ; M1 ; M2."


def test_list_preview_names_rows_by_their_text_column() -> None:
    rows = [(60001, "DOLIPRANE 1000 mg, comprimé"), (60002, "DOLIPRANE 500 mg, gélule")]
    text = describe(_result(["cis", "denomination"], rows))
    assert text == "**2** résultats : DOLIPRANE 1000 mg, comprimé ; DOLIPRANE 500 mg, gélule."


def test_truncated_list_says_so() -> None:
    text = describe(_result(["denomination"], [("A",), ("B",)], truncated=True))
    assert text.startswith("**au moins 2** résultats")
    assert "liste complète est plus longue" in text


def test_empty_result_and_failures() -> None:
    assert describe(_result(["n"], [])).startswith("Aucun résultat")
    assert narrate(Answer("q", abstained=True)) == OUT_OF_SCOPE_MESSAGE
    assert "reformuler" in narrate(Answer("q", error="UnsafeQueryError: …"))


def test_sentence_only_states_what_the_query_returned(conn: sqlite3.Connection) -> None:
    llm = ScriptedLLM("```sql\nSELECT COUNT(*) AS nb FROM medicaments\n```")
    answer = Text2SQL(llm, conn).ask("Combien de spécialités ?")
    assert narrate(answer) == "Réponse : **22** (nb)."


def test_csv_export_is_spreadsheet_friendly() -> None:
    text = to_csv(_result(["denomination", "prix", "taux"], [("A; B", 2.5, None)]))
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    assert rows == [["denomination", "prix", "taux"], ["A; B", "2,5", ""]]


def test_history_keeps_the_latest_questions_first() -> None:
    history = History(size=2)
    ok = Answer("q1", result=_result(["n"], [(1,)]), total_latency_s=1.23)
    history.add(ok, now=datetime(2026, 11, 2, 9, 0, 0))
    history.add(Answer("q2", abstained=True), now=datetime(2026, 11, 2, 9, 1, 0))
    history.add(Answer("q3", error="x"), now=datetime(2026, 11, 2, 9, 2, 0))
    assert len(history) == 2
    assert history.rows() == [
        ["09:02:00", "q3", "erreur", None, 0.0],
        ["09:01:00", "q2", "hors périmètre", None, 0.0],
    ]


@pytest.fixture
def demo(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Module de la démo, chargé sur la base de test (sans serveur LLM)."""
    pytest.importorskip("gradio")
    monkeypatch.setenv("MEDSQL_DATA_DIR", str(db_path.parent))
    spec = importlib.util.spec_from_file_location(
        "demo_app", Path(__file__).parents[1] / "app" / "app.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "demo_app", module)
    spec.loader.exec_module(module)
    return module


def test_demo_answer_fills_sentence_csv_and_history(demo: ModuleType) -> None:
    demo.engine = Text2SQL(
        ScriptedLLM("```sql\nSELECT denomination FROM medicaments LIMIT 4\n```"), demo.conn
    )
    sql, table, status, sentence, download, frame, history = demo.answer(
        "Quels médicaments ?", None
    )
    assert "SELECT" in sql and len(table) == 4 and status.startswith("✅")
    assert sentence.startswith("💬 **4** résultats")
    exported = Path(download.value["path"])
    assert exported.read_bytes().startswith(b"\xef\xbb\xbf")  # BOM : accents lus par un tableur
    assert exported.read_text("utf-8-sig").splitlines()[0] == "denomination"
    assert list(frame["Question"]) == ["Quels médicaments ?"]
    assert len(history) == 1


def test_demo_out_of_scope_has_no_export(demo: ModuleType) -> None:
    demo.engine = Text2SQL(ScriptedLLM("HORS_PERIMETRE"), demo.conn)
    _, table, status, sentence, download, frame, _ = demo.answer("Météo à Lyon ?", None)
    assert table.empty and "Hors périmètre" in status
    assert OUT_OF_SCOPE_MESSAGE in sentence
    assert download.visible is False
    assert list(frame["Issue"]) == ["hors périmètre"]
