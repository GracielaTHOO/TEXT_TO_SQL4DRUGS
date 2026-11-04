from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import httpx
import pytest

from medsql.cache import QueryCache, normalize_question
from medsql.eval.performance import performance
from medsql.llm import OllamaClient
from medsql.llm.base import Completion, Message
from medsql.perf import CpuMeter, cpu_busy_seconds
from medsql.pipeline import Text2SQL
from medsql.report import render_dashboard
from tests.conftest import ScriptedLLM
from tests.test_report import _board_run

COUNT = "```sql\nSELECT COUNT(*) AS n FROM medicaments\n```"


# --- Durées Ollama : premier token et débits -------------------------------------------------


def test_ollama_durations_give_ttft_and_throughput() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "message": {"content": "SELECT 1"},
                "prompt_eval_count": 400,
                "eval_count": 20,
                "load_duration": 500_000_000,
                "prompt_eval_duration": 2_000_000_000,
                "eval_duration": 4_000_000_000,
            },
        )

    client = OllamaClient("m", transport=httpx.MockTransport(handler))
    completion = client.complete([Message("user", "q")])
    assert completion.load_s == pytest.approx(0.5)
    assert completion.ttft_s == pytest.approx(2.5)
    assert completion.tokens_per_s == pytest.approx(5.0)
    assert completion.prompt_tokens_per_s == pytest.approx(200.0)


def test_completion_without_durations_falls_back_to_latency() -> None:
    completion = Completion("x", latency_s=2.0, prompt_tokens=10, completion_tokens=8)
    assert completion.ttft_s is None
    assert completion.prompt_tokens_per_s is None
    assert completion.tokens_per_s == pytest.approx(4.0)
    assert Completion("x", latency_s=0.0, completion_tokens=8).tokens_per_s is None


# --- Coût CPU ---------------------------------------------------------------------------------


def _stat(path: Path, user: int, idle: int) -> None:
    # user nice system idle iowait irq softirq steal
    path.write_text(f"cpu  {user} 0 10 {idle} 5 1 1 0 0 0\ncpu0 1 2 3\n")


def test_cpu_busy_seconds_ignores_idle(tmp_path: Path) -> None:
    stat = tmp_path / "stat"
    _stat(stat, user=100, idle=99_999)
    ticks = os.sysconf("SC_CLK_TCK")
    assert cpu_busy_seconds(stat) == pytest.approx(
        (100 + 10 + 1 + 1) / ticks
    )  # iowait compte comme repos


def test_cpu_meter_measures_the_difference(tmp_path: Path) -> None:
    stat = tmp_path / "stat"
    _stat(stat, user=100, idle=0)
    meter = CpuMeter(stat)
    meter.start()
    ticks = os.sysconf("SC_CLK_TCK")
    _stat(stat, user=100 + 3 * ticks, idle=50)
    assert meter.stop() == pytest.approx(3.0)


def test_cpu_meter_is_none_without_proc_stat(tmp_path: Path) -> None:
    meter = CpuMeter(tmp_path / "absent")
    meter.start()
    assert meter.stop() is None
    (tmp_path / "bad").write_text("intr 1 2 3\n")
    assert cpu_busy_seconds(tmp_path / "bad") is None


# --- Cache des requêtes -----------------------------------------------------------------------


def test_normalize_question_folds_case_accents_and_punctuation() -> None:
    assert normalize_question("  Combien de  MÉDICAMENTS ? ") == normalize_question(
        "combien de medicaments"
    )
    assert normalize_question("A ?") != normalize_question("B ?")


def test_query_cache_is_lru_and_counts() -> None:
    cache = QueryCache(size=2)
    a, b, c = (cache.key("m", "cfg", q) for q in ("a", "b", "c"))
    assert cache.get(a) is None
    cache.put(a, "SELECT 1")
    cache.put(b, "SELECT 2")
    assert cache.get(a) == "SELECT 1"  # a devient le plus récent
    cache.put(c, "SELECT 3")  # b, le plus ancien, sort
    assert cache.get(b) is None
    assert len(cache) == 2
    assert (cache.hits, cache.misses) == (1, 2)
    assert cache.key("m1", "cfg", "a") != cache.key("m2", "cfg", "a")


def test_pipeline_reuses_cached_sql_without_calling_the_llm(conn: sqlite3.Connection) -> None:
    llm = ScriptedLLM(COUNT)
    engine = Text2SQL(llm, conn, cache=QueryCache())
    first = engine.ask("Combien de médicaments ?")
    second = engine.ask("combien de medicaments")
    assert len(llm.calls) == 1
    assert not first.cached and second.cached
    assert second.result is not None and second.result.rows == [(22,)]
    assert second.attempts == 0 and second.ttft_s is None


def test_pipeline_caches_abstentions(conn: sqlite3.Connection) -> None:
    llm = ScriptedLLM("HORS_PERIMETRE")
    engine = Text2SQL(llm, conn, cache=QueryCache())
    engine.ask("Quel temps fera-t-il ?")
    again = engine.ask("Quel temps fera-t-il ?")
    assert again.cached and again.abstained and again.result is None
    assert len(llm.calls) == 1


def test_pipeline_regenerates_when_cached_sql_no_longer_runs(conn: sqlite3.Connection) -> None:
    cache = QueryCache()
    llm = ScriptedLLM(COUNT)
    engine = Text2SQL(llm, conn, cache=cache)
    key = cache.key(llm.model, engine._cache_config, "Combien ?")
    cache.put(key, "SELECT * FROM table_disparue")
    answer = engine.ask("Combien ?")
    assert answer.ok and not answer.cached
    assert len(llm.calls) == 1
    assert cache.get(key) == "SELECT COUNT(*) AS n FROM medicaments"


def test_failed_answers_are_not_cached(conn: sqlite3.Connection) -> None:
    llm = ScriptedLLM("SELECT nb FROM medocs", "SELECT nb FROM medocs")
    cache = QueryCache()
    Text2SQL(llm, conn, max_repairs=0, cache=cache).ask("Combien ?")
    assert len(cache) == 0


def test_cache_is_off_by_default(conn: sqlite3.Connection) -> None:
    llm = ScriptedLLM(COUNT, COUNT)
    engine = Text2SQL(llm, conn)
    engine.ask("Combien ?")
    engine.ask("Combien ?")
    assert len(llm.calls) == 2


# --- Bilan d'un run et tableau de bord --------------------------------------------------------


def _item(ttft: float | None, **extra: float) -> dict[str, float | None]:
    return {"ttft_s": ttft, "prompt_tokens": 400, "completion_tokens": 20, **extra}


def test_performance_aggregates_items() -> None:
    items = [
        _item(1.0, eval_s=2.0, prompt_eval_s=1.0, cpu_s=4.0),
        _item(3.0, eval_s=2.0, prompt_eval_s=1.0, cpu_s=6.0),
        _item(None),  # abstention en cache, erreur réseau : pas de mesure
    ]
    perf = performance(items)
    assert perf["ttft_p50_s"] == pytest.approx(2.0)
    assert perf["generation_tokens_per_s"] == pytest.approx(60 / 4)
    assert perf["prompt_tokens_per_s"] == pytest.approx(1200 / 2)
    assert perf["cpu_s_mean"] == pytest.approx(5.0)
    assert performance([_item(None)]) == {}


def test_dashboard_shows_performance_for_measured_runs() -> None:
    run = _board_run("qwen2.5-coder:7b", [True, False])
    run["summary"]["performance"] = {  # type: ignore[index]
        "ttft_p50_s": 2.5,
        "ttft_p95_s": 4.0,
        "generation_tokens_per_s": 7.3,
        "cpu_s_mean": 30.2,
    }
    run["summary"]["environment"] = {"cpu_count": 4}  # type: ignore[index]
    page = render_dashboard([run])
    assert "<h2>Performance</h2>" in page
    assert "2,5 s" in page and "7,3" in page
    assert "Performance" not in render_dashboard([_board_run("qwen2.5-coder:7b", [True])])
