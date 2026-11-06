"""Pipeline complet : question → SQL → exécution sécurisée → résultat."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field

import httpx

from medsql.cache import QueryCache
from medsql.fewshot import ExampleSelector
from medsql.llm.base import Completion, LLMClient
from medsql.perf import CpuMeter
from medsql.prompting import (
    ABSTAIN_TOKEN,
    PromptConfig,
    build_messages,
    build_repair_messages,
    value_hints,
)
from medsql.sql_guard import (
    ForbiddenQueryError,
    QueryResult,
    UnsafeQueryError,
    extract_sql,
    run_query,
)

OUT_OF_SCOPE_MESSAGE = (
    "Cette question sort du périmètre de la base publique des médicaments : "
    "aucune requête n'a été exécutée."
)

# Une question de la BDPM tient en une ou deux phrases (la plus longue du jeu : 146 caractères).
# Au-delà, le texte n'est pas transmis au modèle : un long texte sert surtout à noyer les
# règles du prompt (injection) et allonge la lecture du prompt sur CPU.
MAX_QUESTION_CHARS = 500
TOO_LONG_ERROR = f"QuestionTropLongue: plus de {MAX_QUESTION_CHARS} caractères, non transmise."


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
    abstained: bool = False  # le modèle a jugé la question hors du périmètre de la base
    examples: list[str] = field(default_factory=list)  # questions des exemples choisis (dynamiques)
    cached: bool = False  # requête reprise du cache, sans appel au LLM
    ttft_s: float | None = None  # temps de premier token du premier appel (Ollama)
    load_s: float = 0.0  # chargement du modèle, cumulé sur les appels
    prompt_eval_s: float = 0.0  # lecture du prompt, cumulée sur les appels
    eval_s: float = 0.0  # génération, cumulée sur les appels
    cpu_s: float | None = None  # temps CPU de la machine pendant la question (Linux)

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
        selector: ExampleSelector | None = None,
        cache: QueryCache | None = None,
    ) -> None:
        self.llm = llm
        self.conn = conn
        self.prompt = prompt or PromptConfig()
        self.max_repairs = max_repairs
        self.max_rows = max_rows
        self.query_timeout_s = query_timeout_s
        self.temperature = temperature
        self.hints = value_hints(conn) if self.prompt.value_hints else ""
        self.selector = selector  # None : exemples fixes
        self.cache = cache  # None : chaque question passe par le LLM (évaluation)
        self._cache_config = repr((self.prompt, max_repairs, temperature, selector is not None))

    def ask(self, question: str) -> Answer:
        answer = Answer(question=question)
        start = time.perf_counter()
        meter = CpuMeter()
        meter.start()
        key = None
        if len(question) > MAX_QUESTION_CHARS:
            answer.error = TOO_LONG_ERROR
            return self._finish(answer, start, meter)
        if self.cache is not None:
            key = self.cache.key(getattr(self.llm, "model", "?"), self._cache_config, question)
            cached = self.cache.get(key)
            if cached is not None and self._answer_from_cache(answer, cached):
                return self._finish(answer, start, meter)
            if cached is not None:
                self.cache.discard(key)  # requête devenue invalide (schéma changé) : on régénère
        self._generate(answer, question)
        if self.cache is not None and key is not None:
            if answer.abstained:
                self.cache.put(key, ABSTAIN_TOKEN)
            elif answer.ok and answer.sql:
                self.cache.put(key, answer.sql)
        return self._finish(answer, start, meter)

    def _finish(self, answer: Answer, start: float, meter: CpuMeter) -> Answer:
        answer.total_latency_s = time.perf_counter() - start
        answer.cpu_s = meter.stop()
        return answer

    def _answer_from_cache(self, answer: Answer, sql: str) -> bool:
        """Rejoue une requête du cache ; ``False`` si elle ne s'exécute plus."""
        answer.cached = True
        if sql == ABSTAIN_TOKEN:
            answer.abstained = True
            return True
        try:
            answer.result = run_query(
                self.conn, sql, max_rows=self.max_rows, timeout_s=self.query_timeout_s
            )
        except (UnsafeQueryError, sqlite3.Error, TimeoutError):
            answer.cached = False
            return False
        answer.sql = sql
        answer.sql_history.append(sql)
        return True

    def _record(self, answer: Answer, completion: Completion) -> None:
        answer.llm_latency_s += completion.latency_s
        answer.prompt_tokens += completion.prompt_tokens or 0
        answer.completion_tokens += completion.completion_tokens or 0
        if answer.ttft_s is None:
            answer.ttft_s = completion.ttft_s
        answer.load_s += completion.load_s or 0.0
        answer.prompt_eval_s += completion.prompt_eval_s or 0.0
        answer.eval_s += completion.eval_s or 0.0

    def _generate(self, answer: Answer, question: str) -> None:
        examples = None
        if self.selector is not None and self.prompt.few_shot:
            chosen = self.selector.select(question)
            examples = [(e.question, e.sql) for e in chosen]
            answer.examples = [e.question for e in chosen]
        messages = build_messages(question, self.prompt, hints=self.hints, examples=examples)
        for attempt in range(self.max_repairs + 1):
            answer.attempts = attempt + 1
            try:
                completion = self.llm.complete(messages, temperature=self.temperature)
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                # Panne ou délai du serveur LLM : la question est comptée fausse,
                # le banc continue avec la suivante.
                answer.error = f"LLMError: {type(exc).__name__}: {exc}"
                break
            self._record(answer, completion)
            if ABSTAIN_TOKEN in completion.text.upper():
                # Abstention : aucune requête n'est exécutée.
                answer.abstained = True
                answer.sql = None
                answer.error = None
                break
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
