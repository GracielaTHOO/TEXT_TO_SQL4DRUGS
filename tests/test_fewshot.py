from __future__ import annotations

import json
import re
import sqlite3

import httpx
import pytest

from medsql.eval.dataset import load_questions
from medsql.fewshot import (
    DEFAULT_K,
    ExampleSelector,
    LexicalEmbedder,
    OllamaEmbedder,
    cosine,
    load_pool,
)
from medsql.pipeline import Text2SQL
from medsql.prompting import ABSTAIN_SHOT, SQL_SHOTS, build_messages
from medsql.sql_guard import run_query, sans_accents, validate
from tests.conftest import ScriptedLLM

POOL = load_pool()
EVAL = [q for q in load_questions() if not q.hors_perimetre]
# Au-delà, un exemple serait une variante d'une question évaluée (une seule valeur changée).
MAX_SIMILARITY = 0.85


def _sql_key(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip().rstrip(";").upper()


def test_pool_starts_with_the_fixed_examples() -> None:
    assert len(POOL) >= 30
    assert [(e.question, e.sql) for e in POOL[: len(SQL_SHOTS)]] == list(SQL_SHOTS)


@pytest.mark.parametrize("example", POOL, ids=lambda e: e.question[:40])
def test_pool_sql_is_safe_and_executes(example, conn: sqlite3.Connection) -> None:  # type: ignore[no-untyped-def]
    validate(example.sql)
    run_query(conn, example.sql, max_rows=None)


def test_pool_is_disjoint_from_the_evaluation_set() -> None:
    eval_questions = {sans_accents(q.question) for q in EVAL}
    eval_sql = {_sql_key(q.sql) for q in EVAL}
    for example in POOL:
        assert sans_accents(example.question) not in eval_questions, example.question
        assert _sql_key(example.sql) not in eval_sql, example.question


def test_no_example_is_a_near_copy_of_an_evaluated_question() -> None:
    selector = ExampleSelector(LexicalEmbedder(), POOL)
    worst = max((selector.scored(q.question)[0][0], q.id) for q in EVAL)
    assert worst[0] < MAX_SIMILARITY, worst


def test_lexical_embedder_ignores_accents_and_case() -> None:
    embedder = LexicalEmbedder()
    a, b, c = embedder.embed(["Paracétamol", "PARACETAMOL", "ibuprofène"])
    assert cosine(a, b) == pytest.approx(1.0)
    assert cosine(a, c) < 0.5


def test_selector_returns_k_examples_closest_last() -> None:
    selector = ExampleSelector(LexicalEmbedder(), POOL)
    chosen = selector.select("Quels médicaments à base de cétirizine sont commercialisés ?")
    assert len(chosen) == DEFAULT_K
    assert chosen[-1].question == "Quels médicaments contiennent de la cétirizine ?"
    scores = [s for s, _ in selector.scored("Quels médicaments à base de cétirizine ?")]
    assert scores == sorted(scores, reverse=True)


def test_ollama_embedder_calls_the_embed_api() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"embeddings": [[1, 0], [0, 1]]})

    embedder = OllamaEmbedder("nomic-embed-text", transport=httpx.MockTransport(handler))
    assert embedder.embed(["a", "b"]) == [[1.0, 0.0], [0.0, 1.0]]
    assert seen == [{"model": "nomic-embed-text", "input": ["a", "b"]}]
    assert embedder.name == "nomic-embed-text"


def test_dynamic_examples_replace_fixed_ones_but_keep_abstention() -> None:
    examples = [("Question A ?", "SELECT 1"), ("Question B ?", "SELECT 2")]
    messages = build_messages("Ma question ?", examples=examples)
    users = [m.content for m in messages if m.role == "user"]
    assert users == [ABSTAIN_SHOT[0], "Question A ?", "Question B ?", "Ma question ?"]
    assert SQL_SHOTS[0][0] not in users


def test_pipeline_records_the_chosen_examples(conn: sqlite3.Connection) -> None:
    llm = ScriptedLLM("```sql\nSELECT COUNT(*) FROM medicaments\n```")
    selector = ExampleSelector(LexicalEmbedder(), POOL)
    answer = Text2SQL(llm, conn, selector=selector).ask("Combien de spécialités BIOGARAN ?")
    assert len(answer.examples) == DEFAULT_K
    sent = [m.content for m in llm.calls[0] if m.role == "user"]
    assert sent[1:-1] == answer.examples
