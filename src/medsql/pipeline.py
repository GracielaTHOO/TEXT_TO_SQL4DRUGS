"""Pipeline complet : question → SQL → exécution sécurisée → résultat."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field

import httpx

from medsql.llm.base import LLMClient
from medsql.prompting import PromptConfig, build_messages, build_repair_messages
from medsql.sql_guard import (
    ForbiddenQueryError,
    QueryResult,
    UnsafeQueryError,
    extract_sql,
    run_query,
)


@dataclass
class Answer:
    question: str
    sql: str | None = None
    result: QueryResult | None = None
    error: str | None = None
    attempts: int = 0
    llm_latency_s: float = 0.0
    total_latency_s: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    sql_history: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.result is not None and self.error is None


class Text2SQL:
    """Orchestre le LLM et la base ; ``max_repairs`` tours d'auto-correction sur erreur SQL."""

    def __init__(
        self,
        llm: LLMClient,
        conn: sqlite3.Connection,
        *,
        prompt: PromptConfig | None = None,
        max_repairs: int = 1,
        max_rows: int | None = 200,
        query_timeout_s: float = 10,
        temperature: float = 0.0,
    ) -> None:
        self.llm = llm
        self.conn = conn
        self.prompt = prompt or PromptConfig()
        self.max_repairs = max_repairs
        self.max_rows = max_rows
        self.query_timeout_s = query_timeout_s
        self.temperature = temperature

    def ask(self, question: str) -> Answer:
        answer = Answer(question=question)
        start = time.perf_counter()
        messages = build_messages(question, self.prompt)
        for attempt in range(self.max_repairs + 1):
            answer.attempts = attempt + 1
            try:
                completion = self.llm.complete(messages, temperature=self.temperature)
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                # Panne ou délai du serveur LLM : la question est comptée fausse,
                # le banc continue avec la suivante.
                answer.error = f"LLMError: {type(exc).__name__}: {exc}"
                break
            answer.llm_latency_s += completion.latency_s
            answer.prompt_tokens += completion.prompt_tokens or 0
            answer.completion_tokens += completion.completion_tokens or 0
            sql = extract_sql(completion.text)
            answer.sql = sql
            answer.sql_history.append(sql)
            try:
                answer.result = run_query(
                    self.conn, sql, max_rows=self.max_rows, timeout_s=self.query_timeout_s
                )
                answer.error = None
                break
            except (UnsafeQueryError, sqlite3.Error, TimeoutError) as exc:
                answer.error = f"{type(exc).__name__}: {exc}"
                # Une requête refusée pour sécurité n'est pas « réparée » : on s'arrête.
                if isinstance(exc, ForbiddenQueryError):
                    break
                messages = build_repair_messages(messages, sql, str(exc))
        answer.total_latency_s = time.perf_counter() - start
        return answer
