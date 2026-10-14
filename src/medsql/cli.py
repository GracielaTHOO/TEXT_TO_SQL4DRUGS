"""Interface en ligne de commande : ``medsql --help``."""

from __future__ import annotations

import json
import logging
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn
from rich.syntax import Syntax
from rich.table import Table

from medsql import __version__
from medsql.config import Settings, get_settings

app = typer.Typer(
    name="medsql",
    help="💊 Text-to-SQL en français sur la Base de données publique des médicaments.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()

ModelOpt = Annotated[
    str | None, typer.Option("--model", "-m", help="Modèle (ex. qwen2.5-coder:7b)")
]
BackendOpt = Annotated[
    str | None, typer.Option("--backend", "-b", help="ollama | openai | vllm | llamacpp")
]
UrlOpt = Annotated[str | None, typer.Option("--base-url", help="URL du serveur LLM")]


def _settings(
    model: str | None = None, backend: str | None = None, url: str | None = None
) -> Settings:
    s = get_settings()
    return replace(
        s,
        model=model or s.model,
        backend=backend or s.backend,
        base_url=url or s.base_url,
    )


@app.callback()
def main(verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False)],
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


@app.command()
def version() -> None:
    """Affiche la version."""
    console.print(f"medsql {__version__}")


@app.command()
def download() -> None:
    """⬇️  Télécharge les fichiers bruts de la BDPM depuis le site de l'ANSM."""
    from medsql.data.download import download_all

    s = _settings()
    files = download_all(s.raw_dir)
    console.print(f"[green]✓[/] {len(files)} fichiers dans {s.raw_dir}")


@app.command()
def build(
    raw_dir: Annotated[Path | None, typer.Option(help="Dossier des fichiers bruts")] = None,
    db: Annotated[Path | None, typer.Option(help="Chemin de la base SQLite")] = None,
) -> None:
    """🧱 Construit la base SQLite normalisée à partir des fichiers bruts."""
    from medsql.data.build_db import build_database

    s = _settings()
    report = build_database(raw_dir or s.raw_dir, db or s.db_path)
    table = Table(title="Tables chargées", show_edge=False)
    table.add_column("Table")
    table.add_column("Lignes", justify="right")
    for name, count in report.rows.items():
        table.add_row(name, f"{count:,}".replace(",", " "))
    console.print(table)
    for name in report.missing_files:
        console.print(f"[yellow]⚠ Fichier absent :[/] {name}")
    console.print(f"[green]✓[/] Base écrite dans {db or s.db_path}")


@app.command()
def setup() -> None:
    """🚀 Télécharge la BDPM puis construit la base (download + build)."""
    download()
    build()


@app.command()
def stats() -> None:
    """📊 Affiche les chiffres clés de la base."""
    from medsql.sql_guard import connect_readonly
    from medsql.stats import key_figures

    with closing(connect_readonly(_settings().db_path)) as conn:
        figures = key_figures(conn)
    table = Table(title="La BDPM en chiffres", show_edge=False)
    table.add_column("Indicateur")
    table.add_column("Valeur", justify="right")
    for kf, value in figures:
        table.add_row(kf.label, f"{value}{' ' + kf.unit if kf.unit else ''}")
    console.print(table)


@app.command()
def ask(
    question: Annotated[str, typer.Argument(help="Question en français")],
    model: ModelOpt = None,
    backend: BackendOpt = None,
    base_url: UrlOpt = None,
) -> None:
    """💬 Pose une question en français et affiche le SQL et le résultat."""
    from medsql.llm import make_client
    from medsql.pipeline import Text2SQL
    from medsql.sql_guard import connect_readonly

    s = _settings(model, backend, base_url)
    with closing(connect_readonly(s.db_path)) as conn:
        engine = Text2SQL(make_client(s), conn, max_rows=s.max_rows)
        with console.status(f"Génération avec {s.model}…"):
            answer = engine.ask(question)
    if answer.sql:
        console.print(Syntax(answer.sql, "sql", theme="ansi_dark", word_wrap=True))
    if answer.error or answer.result is None:
        console.print(f"[red]✗ {answer.error}[/]")
        raise typer.Exit(1)
    table = Table(*answer.result.columns, show_edge=False)
    for row in answer.result.rows:
        table.add_row(*("" if v is None else str(v) for v in row))
    console.print(table)
    console.print(
        f"[dim]{len(answer.result.rows)} ligne(s){' (tronqué)' if answer.result.truncated else ''}"
        f" · {answer.total_latency_s:.1f} s · {answer.attempts} tentative(s)[/]"
    )


@app.command("eval")
def evaluate(
    model: ModelOpt = None,
    backend: BackendOpt = None,
    base_url: UrlOpt = None,
    limit: Annotated[int | None, typer.Option(help="N premières questions (test rapide)")] = None,
    few_shot: Annotated[bool, typer.Option("--few-shot/--zero-shot")] = True,
    hints: Annotated[
        bool,
        typer.Option(
            "--value-hints/--no-value-hints",
            help="Ajouter au prompt les libellés exacts des colonnes catégorielles",
        ),
    ] = False,
    repairs: Annotated[int, typer.Option(help="Tours d'auto-correction sur erreur SQL")] = 1,
    out: Annotated[Path, typer.Option(help="Dossier des runs")] = Path("results/runs"),
    questions: Annotated[Path | None, typer.Option(help="Jeu de questions YAML")] = None,
) -> None:
    """🧪 Évalue un modèle sur le jeu de questions et enregistre le run."""
    from medsql.eval.dataset import load_questions
    from medsql.eval.runner import default_environment, evaluate_item, save_run, summarize
    from medsql.llm import make_client
    from medsql.pipeline import Text2SQL
    from medsql.prompting import PromptConfig
    from medsql.sql_guard import connect_readonly

    s = _settings(model, backend, base_url)
    items = load_questions(questions)[:limit] if limit else load_questions(questions)
    conn = connect_readonly(s.db_path)
    engine = Text2SQL(
        make_client(s),
        conn,
        prompt=PromptConfig(few_shot=few_shot, value_hints=hints),
        max_repairs=repairs,
        max_rows=10_000,
        query_timeout_s=s.query_timeout_s,
        temperature=s.temperature,
    )
    results = []
    progress = Progress(
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("[green]{task.fields[ok]} ✓"),
        TimeElapsedColumn(),
        console=console,
    )
    with progress:
        task = progress.add_task(s.model, total=len(items), ok=0)
        for item in items:
            result = evaluate_item(engine, conn, item)
            results.append(result)
            progress.update(task, advance=1, ok=sum(r.correct for r in results))
    summary = summarize(
        results,
        model=s.model,
        backend=s.backend,
        config={
            "few_shot": few_shot,
            "value_hints": hints,
            "max_repairs": repairs,
            "temperature": s.temperature,
            "limit": limit,
        },
        environment=default_environment(items, s.db_path),
    )
    conn.close()
    path = save_run(summary, results, out)
    console.print(
        f"\n[bold]Exactitude : {100 * summary.accuracy:.1f} %[/] "
        f"(stricte {100 * summary.accuracy_strict:.1f} %, exécutable "
        f"{100 * summary.executable_rate:.1f} %, p50 {summary.latency_p50_s:.1f} s)"
    )
    for warning in summary.warnings:
        console.print(f"[yellow]⚠ {warning}[/]")
    console.print(f"[green]✓[/] Run enregistré : {path}")


@app.command()
def report(
    runs_dir: Annotated[Path, typer.Option(help="Dossier des runs")] = Path("results/runs"),
    out: Annotated[Path, typer.Option(help="Fichier HTML")] = Path("results/dashboard.html"),
    readme: Annotated[Path, typer.Option(help="README à mettre à jour")] = Path("README.md"),
    with_stats: Annotated[bool, typer.Option(help="Inclure les chiffres de la base")] = True,
) -> None:
    """📈 Génère le tableau de bord HTML et met à jour le tableau du README."""
    from medsql.eval.runner import load_runs
    from medsql.report import render_dashboard, update_readme

    runs = load_runs(runs_dir) if runs_dir.exists() else []
    figures: list[tuple[str, str]] = []
    db_path = _settings().db_path
    if with_stats and db_path.exists():
        from medsql.sql_guard import connect_readonly
        from medsql.stats import key_figures

        with closing(connect_readonly(db_path)) as conn:
            values = key_figures(conn)
        for kf, value in values:
            shown = f"{value:,}".replace(",", " ") if isinstance(value, int) else str(value)
            figures.append((kf.label, f"{shown}{' ' + kf.unit if kf.unit else ''}"))
        out.parent.mkdir(parents=True, exist_ok=True)
        (out.parent / "bdpm_stats.json").write_text(
            json.dumps(dict(figures), indent=2, ensure_ascii=False) + "\n", "utf-8"
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_dashboard(runs, figures), "utf-8")
    console.print(f"[green]✓[/] Tableau de bord : {out} ({len(runs)} run(s))")
    if readme.exists() and update_readme(readme, runs):
        console.print(f"[green]✓[/] Tableau de résultats mis à jour dans {readme}")


@app.command()
def profile(
    out: Annotated[Path, typer.Option(help="Fichier Markdown")] = Path("docs/donnees-profil.md"),
) -> None:
    """🔬 Génère le profil de la base (volumétrie, complétude, valeurs fréquentes)."""
    from medsql.profile import profile_markdown
    from medsql.sql_guard import connect_readonly

    s = _settings()
    manifest = s.raw_dir / "manifest.json"
    downloaded_at = (
        json.loads(manifest.read_text("utf-8"))["downloaded_at"] if manifest.exists() else None
    )
    with closing(connect_readonly(s.db_path)) as conn:
        out.write_text(profile_markdown(conn, downloaded_at=downloaded_at), "utf-8")
    console.print(f"[green]✓[/] {out}")


@app.command("check-questions")
def check_questions_cmd(
    out: Annotated[Path, typer.Option(help="Rapport JSON")] = Path("results/questions_check.json"),
    questions: Annotated[Path | None, typer.Option(help="Jeu de questions YAML")] = None,
) -> None:
    """🩺 Exécute les requêtes de référence sur la base et liste les questions à revoir."""
    from medsql.eval.dataset import load_questions
    from medsql.profile import check_questions, checks_as_dict
    from medsql.sql_guard import connect_readonly

    with closing(connect_readonly(_settings().db_path)) as conn:
        checks = check_questions(conn, load_questions(questions))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(checks_as_dict(checks), indent=2, ensure_ascii=False) + "\n", "utf-8")
    review = [c for c in checks if c.needs_review]
    for c in review:
        reason = c.error or ("valeur nulle" if c.degenerate else "0 ligne")
        console.print(f"[yellow]⚠ {c.id}[/] : {reason}")
    console.print(
        f"[green]✓[/] {len(checks) - len(review)}/{len(checks)} questions valides · {out}"
    )


@app.command()
def docs(
    out: Annotated[Path, typer.Option(help="Fichier Markdown")] = Path("docs/data.md"),
) -> None:
    """📚 Régénère le dictionnaire de données à partir du schéma."""
    from medsql.docs import data_dictionary

    out.write_text(data_dictionary(), "utf-8")
    console.print(f"[green]✓[/] {out}")


if __name__ == "__main__":
    app()
