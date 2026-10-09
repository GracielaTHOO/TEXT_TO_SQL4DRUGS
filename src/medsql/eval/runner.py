"""Exécution du banc d'évaluation et agrégation des résultats."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import sqlite3
import statistics
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from medsql import __version__
from medsql.eval.dataset import EvalItem
from medsql.eval.metrics import soft_match, strict_match
from medsql.pipeline import Answer, Text2SQL
from medsql.sql_guard import run_query

EVAL_ROW_CAP = 10_000


@dataclass
class ItemResult:
    id: str
    question: str
    difficulte: str
    categorie: str
    gold_sql: str
    pred_sql: str | None
    correct: bool
    correct_strict: bool
    executable: bool
    error: str | None
    attempts: int
    llm_latency_s: float
    total_latency_s: float
    prompt_tokens: int
    completion_tokens: int
    gold_rows: int
    pred_rows: int | None


@dataclass
class RunSummary:
    run_id: str
    created_at: str
    model: str
    backend: str
    config: dict[str, object]
    environment: dict[str, str]
    n: int
    accuracy: float
    accuracy_strict: float
    executable_rate: float
    repaired: int
    latency_p50_s: float
    latency_p95_s: float
    latency_mean_s: float
    tokens_per_question: float
    by_difficulty: dict[str, dict[str, float]]
    by_category: dict[str, dict[str, float]]
    warnings: list[str] = field(default_factory=list)


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def _group(
    results: list[ItemResult], key: Callable[[ItemResult], str]
) -> dict[str, dict[str, float]]:
    groups: dict[str, list[ItemResult]] = {}
    for r in results:
        groups.setdefault(key(r), []).append(r)
    return {
        name: {"n": len(items), "accuracy": sum(i.correct for i in items) / len(items)}
        for name, items in sorted(groups.items())
    }


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "inconnu"


def dataset_fingerprint(items: list[EvalItem]) -> str:
    payload = json.dumps([asdict(i) for i in items], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def evaluate_item(engine: Text2SQL, conn: sqlite3.Connection, item: EvalItem) -> ItemResult:
    gold = run_query(conn, item.sql, max_rows=EVAL_ROW_CAP, timeout_s=60)
    try:
        answer = engine.ask(item.question)
    except Exception as exc:
        answer = Answer(question=item.question, error=f"{type(exc).__name__}: {exc}", attempts=1)
    pred_rows = answer.result.rows if answer.result else None
    correct = strict = False
    if pred_rows is not None:
        correct = soft_match(gold.rows, pred_rows, ordered=item.ordonne)
        strict = strict_match(gold.rows, pred_rows, ordered=item.ordonne)
    return ItemResult(
        id=item.id,
        question=item.question,
        difficulte=item.difficulte,
        categorie=item.categorie,
        gold_sql=item.sql,
        pred_sql=answer.sql,
        correct=correct,
        correct_strict=strict,
        executable=answer.ok,
        error=answer.error,
        attempts=answer.attempts,
        llm_latency_s=round(answer.llm_latency_s, 3),
        total_latency_s=round(answer.total_latency_s, 3),
        prompt_tokens=answer.prompt_tokens,
        completion_tokens=answer.completion_tokens,
        gold_rows=len(gold.rows),
        pred_rows=len(pred_rows) if pred_rows is not None else None,
    )


def summarize(
    results: list[ItemResult],
    *,
    model: str,
    backend: str,
    config: dict[str, object],
    environment: dict[str, str] | None = None,
) -> RunSummary:
    n = len(results)
    latencies = [r.total_latency_s for r in results]
    warnings = [
        f"{r.id} : la requête de référence renvoie 0 ligne (question à revoir)"
        for r in results
        if r.gold_rows == 0
    ]
    now = datetime.now(timezone.utc)
    slug = re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")
    return RunSummary(
        run_id=f"{now:%Y%m%dT%H%M%S}_{slug}",
        created_at=now.isoformat(timespec="seconds"),
        model=model,
        backend=backend,
        config=config,
        environment=environment or {},
        n=n,
        accuracy=sum(r.correct for r in results) / n if n else 0.0,
        accuracy_strict=sum(r.correct_strict for r in results) / n if n else 0.0,
        executable_rate=sum(r.executable for r in results) / n if n else 0.0,
        repaired=sum(r.attempts > 1 and r.executable for r in results),
        latency_p50_s=round(_percentile(latencies, 0.5), 3),
        latency_p95_s=round(_percentile(latencies, 0.95), 3),
        latency_mean_s=round(statistics.fmean(latencies), 3) if latencies else 0.0,
        tokens_per_question=(
            round(sum(r.prompt_tokens + r.completion_tokens for r in results) / n, 1) if n else 0.0
        ),
        by_difficulty=_group(results, lambda r: r.difficulte),
        by_category=_group(results, lambda r: r.categorie),
        warnings=warnings,
    )


def default_environment(items: list[EvalItem], db_path: Path) -> dict[str, str]:
    env = {
        "medsql": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(terse=True),
        "git_commit": _git_commit(),
        "dataset_sha": dataset_fingerprint(items),
    }
    manifest = db_path.parent / "raw" / "manifest.json"
    if manifest.exists():
        env["bdpm_downloaded_at"] = json.loads(manifest.read_text("utf-8"))["downloaded_at"]
    return env


def save_run(summary: RunSummary, results: list[ItemResult], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{summary.run_id}.json"
    payload = {"summary": asdict(summary), "items": [asdict(r) for r in results]}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", "utf-8")
    return path


def load_runs(runs_dir: Path) -> list[dict[str, object]]:
    """Charge tous les runs, du plus ancien au plus récent."""
    runs = [json.loads(p.read_text("utf-8")) for p in sorted(runs_dir.glob("*.json"))]
    return sorted(runs, key=lambda r: str(r["summary"]["created_at"]))
