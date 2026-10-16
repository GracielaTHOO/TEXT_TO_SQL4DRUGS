from __future__ import annotations

import sqlite3

import httpx

from medsql.eval.dataset import load_questions
from medsql.eval.runner import evaluate_item, summarize
from medsql.pipeline import Text2SQL
from medsql.prompting import MAX_HINT_VALUES, PromptConfig, build_messages, value_hints
from tests.conftest import OracleLLM, ScriptedLLM


def test_answer_happy_path(conn: sqlite3.Connection) -> None:
    llm = ScriptedLLM("```sql\nSELECT COUNT(*) AS n FROM medicaments\n```")
    answer = Text2SQL(llm, conn).ask("Combien ?")
    assert answer.ok
    assert answer.result is not None
    assert answer.result.rows == [(22,)]
    assert answer.attempts == 1


def test_self_repair_on_sql_error(conn: sqlite3.Connection) -> None:
    llm = ScriptedLLM("SELECT nb FROM medocs", "SELECT COUNT(*) FROM medicaments")
    answer = Text2SQL(llm, conn, max_repairs=1).ask("Combien ?")
    assert answer.ok
    assert answer.attempts == 2
    assert "no such table" in llm.calls[1][-1].content


def test_no_repair_on_forbidden_query(conn: sqlite3.Connection) -> None:
    llm = ScriptedLLM("DROP TABLE medicaments", "SELECT 1")
    answer = Text2SQL(llm, conn, max_repairs=1).ask("Supprime tout")
    assert not answer.ok
    assert answer.attempts == 1


def test_prompt_contains_schema_and_question() -> None:
    messages = build_messages("Ma question ?")
    assert "CREATE TABLE medicaments" in messages[0].content
    assert "sans_accents" in messages[0].content
    assert messages[-1].content == "Ma question ?"


def test_oracle_scores_100_percent(conn: sqlite3.Connection) -> None:
    engine = Text2SQL(OracleLLM(), conn, max_rows=10_000)
    items = load_questions()
    results = [evaluate_item(engine, conn, item) for item in items]
    summary = summarize(results, model="oracle", backend="test", config={})
    assert summary.accuracy == 1.0
    assert summary.accuracy_strict == 1.0
    assert summary.executable_rate == 1.0
    assert set(summary.by_difficulty) == {"facile", "moyen", "difficile"}


class _TimeoutLLM:
    model = "timeout"

    def complete(self, messages, *, temperature=0.0):  # type: ignore[no-untyped-def]
        raise httpx.ReadTimeout("timed out")


def test_llm_failure_is_recorded_not_raised(conn: sqlite3.Connection) -> None:
    answer = Text2SQL(_TimeoutLLM(), conn).ask("Combien ?")
    assert not answer.ok
    assert answer.error is not None
    assert answer.error.startswith("LLMError: ReadTimeout")


def test_unterminated_string_is_repaired(conn: sqlite3.Connection) -> None:
    llm = ScriptedLLM("SELECT 'abc", "SELECT COUNT(*) FROM medicaments")
    answer = Text2SQL(llm, conn, max_repairs=1).ask("Combien ?")
    assert answer.ok
    assert answer.attempts == 2


class _CrashingEngine:
    def ask(self, question: str) -> None:
        raise RuntimeError("panne inattendue")


def test_evaluate_item_survives_unexpected_errors(conn: sqlite3.Connection) -> None:
    item = load_questions()[0]
    result = evaluate_item(_CrashingEngine(), conn, item)  # type: ignore[arg-type]
    assert not result.correct
    assert result.error == "RuntimeError: panne inattendue"


def test_value_hints_list_exact_labels(conn: sqlite3.Connection) -> None:
    hints = value_hints(conn)
    assert "medicaments.etat_commercialisation : 'Commercialisée'" in hints
    # Colonne à texte libre (trop de valeurs distinctes) : non listée.
    assert all(len(line.split(", ")) <= MAX_HINT_VALUES for line in hints.splitlines())


def test_value_hints_are_on_by_default_and_can_be_disabled(conn: sqlite3.Connection) -> None:
    sql = "```sql\nSELECT COUNT(*) FROM medicaments\n```"
    plain, hinted = ScriptedLLM(sql), ScriptedLLM(sql)
    Text2SQL(plain, conn, prompt=PromptConfig(value_hints=False)).ask("Combien ?")
    Text2SQL(hinted, conn).ask("Combien ?")
    assert "Valeurs exactes" not in plain.calls[0][0].content
    assert "Valeurs exactes" in hinted.calls[0][0].content


def test_value_hints_quote_like_sql() -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE disponibilites (statut TEXT)")
    conn.execute("INSERT INTO disponibilites VALUES ('Tension d''approvisionnement')")
    assert "'Tension d''approvisionnement'" in value_hints(conn)
    conn.close()
