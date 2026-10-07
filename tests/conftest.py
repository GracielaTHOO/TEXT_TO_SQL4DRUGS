from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from medsql.data.build_db import build_database
from medsql.eval.dataset import load_questions
from medsql.llm.base import Completion, Message
from medsql.sql_guard import connect_readonly

FIXTURES = Path(__file__).parent / "fixtures" / "bdpm"


class ScriptedLLM:
    """Faux LLM : renvoie les réponses fournies, dans l'ordre."""

    model = "scripted"

    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.calls: list[list[Message]] = []

    def complete(self, messages: list[Message], *, temperature: float = 0.0) -> Completion:
        self.calls.append(messages)
        return Completion(
            self.responses.pop(0), latency_s=0.01, prompt_tokens=100, completion_tokens=20
        )


class OracleLLM:
    """Faux LLM « parfait » : renvoie le SQL de référence de la question posée."""

    model = "oracle"

    def __init__(self) -> None:
        self.gold = {q.question: q.sql for q in load_questions()}

    def complete(self, messages: list[Message], *, temperature: float = 0.0) -> Completion:
        return Completion(f"```sql\n{self.gold[messages[-1].content]}\n```", latency_s=0.01)


@pytest.fixture(scope="session")
def db_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("db") / "bdpm.sqlite"
    build_database(FIXTURES, path)
    return path


@pytest.fixture
def conn(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect_readonly(db_path)
    yield connection
    connection.close()
