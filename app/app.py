"""Démo Gradio : posez une question en français sur les médicaments.

Lancement local :  python app/app.py   (nécessite `medsql setup` et un serveur Ollama)
Sur Hugging Face Spaces, voir space/ (image Docker avec Ollama embarqué).
"""

from __future__ import annotations

import html
import os
from pathlib import Path

import gradio as gr
import pandas as pd

from medsql.config import get_settings
from medsql.data.schema import TABLES
from medsql.eval.runner import load_runs
from medsql.llm import make_client
from medsql.pipeline import Text2SQL
from medsql.report import render_dashboard
from medsql.sql_guard import connect_readonly
from medsql.stats import key_figures

ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = Path(os.environ.get("MEDSQL_RUNS_DIR", ROOT / "results" / "runs"))

EXAMPLES = [
    "Combien de médicaments sont actuellement commercialisés ?",
    "Quels médicaments contenant de l'amoxicilline sont en rupture de stock ?",
    "Quels sont les génériques du DOLIPRANE 1000 mg ?",
    "Quelles sont les 5 substances actives présentes dans le plus de spécialités ?",
    "Quel est le prix moyen d'une boîte de médicament à base de metformine ?",
    "Quels médicaments ont obtenu une ASMR de niveau I ?",
    "Combien de spécialités sont réservées à l'usage hospitalier ?",
]

settings = get_settings()
conn = connect_readonly(settings.db_path)
engine = Text2SQL(make_client(settings), conn, max_rows=settings.max_rows)


def answer(question: str) -> tuple[str, pd.DataFrame, str]:
    if not question or not question.strip():
        return "", pd.DataFrame(), "✏️ Saisissez une question."
    result = engine.ask(question)
    sql = result.sql or ""
    if result.error or result.result is None:
        return sql, pd.DataFrame(), f"❌ {result.error}"
    df = pd.DataFrame(result.result.rows, columns=result.result.columns)
    status = (
        f"✅ {len(df)} ligne(s){' (tronqué)' if result.result.truncated else ''} · "
        f"{result.total_latency_s:.1f} s · {settings.model}"
        + (" · 🔁 requête auto-corrigée" if result.attempts > 1 else "")
    )
    return sql, df, status


def figures_markdown() -> str:
    lines = ["| Indicateur | Valeur |", "|---|---:|"]
    for kf, value in key_figures(conn):
        shown = f"{value:,}".replace(",", " ") if isinstance(value, int) else str(value)
        lines.append(f"| {kf.label} | {shown}{' ' + kf.unit if kf.unit else ''} |")
    return "\n".join(lines)


def dashboard_iframe() -> str:
    runs = load_runs(RUNS_DIR) if RUNS_DIR.exists() else []
    page = render_dashboard(runs)
    return (
        f'<iframe srcdoc="{html.escape(page)}" style="width:100%;height:1400px;border:0" '
        'title="Tableau de bord"></iframe>'
    )


def schema_markdown() -> str:
    parts = []
    for t in TABLES:
        cols = "\n".join(f"- `{c.name}` *{c.sql_type}* : {c.description}" for c in t.columns)
        parts.append(f"### 🗂️ `{t.name}`\n{t.description}\n\n{cols}")
    return "\n\n".join(parts)


with gr.Blocks(title="Text-to-SQL médicaments") as demo:
    gr.Markdown(
        "# 💊 Text-to-SQL médicaments\n"
        "Interrogez en français la **Base de données publique des médicaments** (ANSM). "
        f"Un LLM local (`{settings.model}`) traduit la question en SQL, exécutée en lecture seule."
    )
    with gr.Tab("💬 Interroger"):
        question = gr.Textbox(
            label="Votre question", placeholder="Ex. : quels médicaments sont en rupture de stock ?"
        )
        ask_btn = gr.Button("🔎 Interroger la base", variant="primary")
        status = gr.Markdown()
        sql_out = gr.Code(label="🧾 SQL généré", language="sql")
        table_out = gr.Dataframe(label="📋 Résultat", wrap=True)
        gr.Examples(EXAMPLES, inputs=question, label="💡 Exemples")
        ask_btn.click(answer, question, [sql_out, table_out, status])
        question.submit(answer, question, [sql_out, table_out, status])
    with gr.Tab("📈 Évaluation"):
        gr.HTML(dashboard_iframe())
    with gr.Tab("📊 La base en chiffres"):
        gr.Markdown(figures_markdown())
    with gr.Tab("🗂️ Schéma"):
        gr.Markdown(schema_markdown())
    with gr.Tab("ℹ️ À propos"):
        gr.Markdown(
            "**Données** : BDPM, ANSM, licence ouverte, mise à jour mensuelle.  \n"
            "**Sécurité** : une seule requête `SELECT`, vérifiée par analyse syntaxique, base ouverte "
            "en lecture seule, autorisateur SQLite, délai maximal.  \n"
            "**Avertissement** : démonstration technique, ne constitue pas un avis médical.  \n"
            "**Code** : [github.com/GracielaTHOO/TEXT_TO_SQL4DRUGS]"
            "(https://github.com/GracielaTHOO/TEXT_TO_SQL4DRUGS)"
        )

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=2).launch(
        server_name=os.environ.get("GRADIO_SERVER_NAME", "127.0.0.1"),
        theme=gr.themes.Soft(primary_hue="blue"),
    )
