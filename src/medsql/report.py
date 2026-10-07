"""Tableau de bord HTML autonome et tableau de résultats du README.

Le tableau de bord est un fichier HTML unique, sans dépendance externe (SVG en ligne,
CSS et JS embarqués) : il s'ouvre hors ligne et se publie tel quel sur GitHub Pages.
"""

from __future__ import annotations

import html
import re
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from medsql.eval.dataset import CATEGORIES, DIFFICULTIES

README_START = "<!-- RESULTS:START -->"
README_END = "<!-- RESULTS:END -->"

Run = dict[str, Any]


# --------------------------------------------------------------------------- sélection


def config_label(summary: dict[str, Any]) -> str:
    cfg = summary.get("config", {})
    parts = [str(summary["model"])]
    if not cfg.get("few_shot", True):
        parts.append("zero-shot")
    if cfg.get("max_repairs", 1) == 0:
        parts.append("sans auto-correction")
    return " · ".join(parts)


def latest_per_config(runs: Sequence[Run]) -> list[Run]:
    """Dernier run complet de chaque configuration, du meilleur au moins bon."""
    latest: dict[str, Run] = {}
    for run in runs:  # runs triés du plus ancien au plus récent
        s = run["summary"]
        if s.get("config", {}).get("limit"):
            continue  # les runs partiels (--limit) ne vont pas au classement
        latest[config_label(s)] = run
    return sorted(latest.values(), key=lambda r: -float(r["summary"]["accuracy"]))


# --------------------------------------------------------------------------- README


def _pct(x: float) -> str:
    return f"{100 * x:.1f} %".replace(".", ",")


def _sec(x: float) -> str:
    return f"{x:.1f} s".replace(".", ",")


def readme_table(runs: Sequence[Run]) -> str:
    board = latest_per_config(runs)
    if not board:
        return "_Aucun run d'évaluation complet pour l'instant. Lancez `medsql eval`._"
    lines = [
        "| Modèle | Exactitude | Exactitude stricte | SQL exécutable | Latence p50 | Latence p95 | Date |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for run in board:
        s = run["summary"]
        lines.append(
            f"| {config_label(s)} | **{_pct(s['accuracy'])}** | {_pct(s['accuracy_strict'])} "
            f"| {_pct(s['executable_rate'])} | {_sec(s['latency_p50_s'])} "
            f"| {_sec(s['latency_p95_s'])} | {s['created_at'][:10]} |"
        )
    n = board[0]["summary"]["n"]
    lines.append("")
    lines.append(
        f"_{n} questions · exactitude = résultat d'exécution identique à la référence "
        "(voir [docs/evaluation.md](docs/evaluation.md))._"
    )
    return "\n".join(lines)


def update_readme(readme: Path, runs: Sequence[Run]) -> bool:
    """Remplace le bloc entre les marqueurs RESULTS ; renvoie True si le fichier a changé."""
    text = readme.read_text("utf-8")
    pattern = re.compile(re.escape(README_START) + r".*?" + re.escape(README_END), re.DOTALL)
    if not pattern.search(text):
        return False
    new = pattern.sub(f"{README_START}\n{readme_table(runs)}\n{README_END}", text)
    if new != text:
        readme.write_text(new, "utf-8")
        return True
    return False


# --------------------------------------------------------------------------- HTML

_CSS = """
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;
--muted:#898781;--grid:#e1e0d9;--border:rgba(11,11,11,.10);--accent:#2a78d6;
--good:#0ca30c;--good-ink:#006300;--crit:#d03b3b;
--s100:#cde2fb;--s250:#86b6ef;--s400:#3987e5;--s550:#1c5cab;--s700:#0d366b}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;
--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--grid:#2c2c2a;
--border:rgba(255,255,255,.10);--accent:#3987e5;--good-ink:#0ca30c}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;
--ink2:#c3c2b7;--grid:#2c2c2a;--border:rgba(255,255,255,.10);--accent:#3987e5;--good-ink:#0ca30c}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);
font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1120px;margin:0 auto;padding:32px 16px 64px}
header{display:flex;gap:16px;align-items:center;margin-bottom:8px}
header svg{flex:none}
h1{font-size:26px;margin:0}h2{font-size:18px;margin:40px 0 4px}
.sub{color:var(--ink2);margin:0 0 24px}.note{color:var(--muted);font-size:13px;margin:4px 0 12px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px}
.tile .v{font-size:28px;font-weight:650}.tile .l{color:var(--ink2);font-size:13px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px;
overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:8px 10px;border-bottom:1px solid var(--grid);text-align:left;white-space:nowrap}
th{color:var(--ink2);font-weight:600}td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.ok{color:var(--good-ink);font-weight:600}.ko{color:var(--crit);font-weight:600}
code{font:12px ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap}
details summary{cursor:pointer;color:var(--ink2)}
svg text{fill:var(--ink2);font:12px system-ui,sans-serif}
svg .val{fill:var(--ink);font-weight:600}
#tip{position:fixed;pointer-events:none;background:var(--surface);color:var(--ink);
border:1px solid var(--border);border-radius:8px;padding:6px 10px;font-size:13px;
box-shadow:0 4px 16px rgba(0,0,0,.12);display:none;z-index:10}
footer{margin-top:48px;color:var(--muted);font-size:13px}
"""

_JS = """
const tip=document.getElementById('tip');
document.querySelectorAll('[data-tip]').forEach(el=>{
 el.addEventListener('mousemove',e=>{tip.textContent=el.dataset.tip;tip.style.display='block';
  tip.style.left=Math.min(e.clientX+12,innerWidth-tip.offsetWidth-8)+'px';tip.style.top=(e.clientY+12)+'px'});
 el.addEventListener('mouseleave',()=>tip.style.display='none');});
"""

LOGO_SVG = """<svg width="44" height="44" viewBox="0 0 64 64" aria-hidden="true">
<rect width="64" height="64" rx="14" fill="#2a78d6"/>
<rect x="14" y="26" width="36" height="14" rx="7" fill="#fff"/>
<rect x="32" y="26" width="18" height="14" rx="7" fill="#cde2fb"/>
<path d="M18 48h28M18 53h18" stroke="#cde2fb" stroke-width="3" stroke-linecap="round"/>
<path d="M18 12l6 6-6 6M28 24h10" stroke="#fff" stroke-width="3" fill="none"
 stroke-linecap="round" stroke-linejoin="round"/></svg>"""


def _e(x: object) -> str:
    return html.escape(str(x))


def _tile(value: str, label: str) -> str:
    return (
        f'<div class="tile"><div class="v">{_e(value)}</div><div class="l">{_e(label)}</div></div>'
    )


def _bar_chart(rows: list[tuple[str, float]]) -> str:
    """Barres horizontales (une série) : exactitude par configuration."""
    label_w, bar_w, row_h = 260, 560, 34
    height = row_h * len(rows) + 28
    parts = [
        f'<svg viewBox="0 0 {label_w + bar_w + 70} {height}" width="100%" role="img" '
        'aria-label="Exactitude par configuration">'
    ]
    for t in (0, 0.25, 0.5, 0.75, 1):
        x = label_w + t * bar_w
        parts.append(f'<line x1="{x}" x2="{x}" y1="0" y2="{height - 22}" stroke="var(--grid)"/>')
        parts.append(f'<text x="{x}" y="{height - 6}" text-anchor="middle">{int(t * 100)} %</text>')
    for i, (name, acc) in enumerate(rows):
        y = i * row_h + 6
        w = max(acc * bar_w, 2)
        parts.append(f'<text x="{label_w - 10}" y="{y + 16}" text-anchor="end">{_e(name)}</text>')
        parts.append(
            f'<rect x="{label_w}" y="{y + 3}" width="{w:.1f}" height="18" rx="4" fill="var(--accent)" '
            f'data-tip="{_e(name)} : {_pct(acc)}"/>'
        )
        parts.append(f'<text class="val" x="{label_w + w + 8:.1f}" y="{y + 16}">{_pct(acc)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _seq_color(x: float) -> tuple[str, str]:
    """Rampe séquentielle bleue (une teinte) ; renvoie (fond, encre lisible)."""
    steps = [(0.2, "var(--s100)"), (0.4, "var(--s250)"), (0.6, "var(--s400)"), (0.8, "var(--s550)")]
    for limit, color in steps:
        if x < limit:
            return color, "#0b0b0b" if limit <= 0.4 else "#ffffff"
    return "var(--s700)", "#ffffff"


def _heatmap(board: list[Run], key: str, order: Sequence[str]) -> str:
    head = "".join(f'<th class="n">{_e(config_label(r["summary"]))}</th>' for r in board)
    body = []
    for name in order:
        cells = []
        for run in board:
            stat = run["summary"][key].get(name)
            if not stat:
                cells.append('<td class="n">–</td>')
                continue
            bg, fg = _seq_color(stat["accuracy"])
            tip = f"{config_label(run['summary'])} · {name} : {_pct(stat['accuracy'])} sur {stat['n']} questions"
            cells.append(
                f'<td class="n" style="background:{bg};color:{fg}" data-tip="{_e(tip)}">'
                f"{_pct(stat['accuracy'])}</td>"
            )
        body.append(f"<tr><th>{_e(name)}</th>{''.join(cells)}</tr>")
    return f"<table><thead><tr><th></th>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _leaderboard(board: list[Run]) -> str:
    rows = []
    for rank, run in enumerate(board, 1):
        s = run["summary"]
        rows.append(
            f"<tr><td class='n'>{rank}</td><td>{_e(config_label(s))}</td><td>{_e(s['backend'])}</td>"
            f"<td class='n'><b>{_pct(s['accuracy'])}</b></td><td class='n'>{_pct(s['accuracy_strict'])}</td>"
            f"<td class='n'>{_pct(s['executable_rate'])}</td><td class='n'>{s['repaired']}</td>"
            f"<td class='n'>{_sec(s['latency_p50_s'])}</td><td class='n'>{_sec(s['latency_p95_s'])}</td>"
            f"<td class='n'>{s['tokens_per_question']:.0f}</td><td>{_e(s['created_at'][:10])}</td></tr>"
        )
    return (
        "<table><thead><tr><th class='n'>#</th><th>Configuration</th><th>Backend</th>"
        "<th class='n'>Exactitude</th><th class='n'>Stricte</th><th class='n'>Exécutable</th>"
        "<th class='n'>Réparées</th><th class='n'>p50</th><th class='n'>p95</th>"
        "<th class='n'>Tokens/question</th><th>Date</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _questions(run: Run) -> str:
    rows = []
    for item in run["items"]:
        mark = (
            '<span class="ok">✓ juste</span>'
            if item["correct"]
            else '<span class="ko">✗ faux</span>'
        )
        detail = (
            f"<details><summary>SQL</summary><p><b>Généré</b></p><code>{_e(item['pred_sql'] or '—')}</code>"
            f"<p><b>Référence</b></p><code>{_e(item['gold_sql'])}</code>"
            + (f"<p class='ko'>{_e(item['error'])}</p>" if item.get("error") else "")
            + "</details>"
        )
        rows.append(
            f"<tr><td>{_e(item['id'])}</td><td style='white-space:normal'>{_e(item['question'])}{detail}</td>"
            f"<td>{_e(item['difficulte'])}</td><td>{mark}</td>"
            f"<td class='n'>{_sec(item['total_latency_s'])}</td></tr>"
        )
    return (
        "<table><thead><tr><th>Id</th><th>Question</th><th>Difficulté</th><th>Résultat</th>"
        f"<th class='n'>Latence</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


def render_dashboard(runs: Sequence[Run], figures: Sequence[tuple[str, str]] | None = None) -> str:
    board = latest_per_config(runs)
    generated = datetime.now().strftime("%d/%m/%Y %H:%M")
    sections: list[str] = []
    if figures:
        sections.append("<h2>La base en chiffres</h2><p class='note'>BDPM, ANSM.</p>")
        sections.append(
            '<div class="tiles">' + "".join(_tile(v, label) for label, v in figures) + "</div>"
        )
    if board:
        best = board[0]["summary"]
        sections.append("<h2>Meilleure configuration</h2>")
        sections.append(
            '<div class="tiles">'
            + _tile(_pct(best["accuracy"]), f"Exactitude · {config_label(best)}")
            + _tile(_pct(best["executable_rate"]), "Requêtes exécutables")
            + _tile(_sec(best["latency_p50_s"]), "Latence médiane par question")
            + _tile(str(best["n"]), "Questions évaluées")
            + _tile(str(len(board)), "Configurations comparées")
            + "</div>"
        )
        sections.append("<h2>Exactitude par configuration</h2>")
        sections.append(
            "<p class='note'>Part des questions dont le résultat d'exécution est identique à la référence.</p>"
        )
        bars = [(config_label(r["summary"]), float(r["summary"]["accuracy"])) for r in board]
        sections.append(f'<div class="card">{_bar_chart(bars)}</div>')
        sections.append("<h2>Classement détaillé</h2>")
        sections.append(f'<div class="card">{_leaderboard(board)}</div>')
        sections.append("<h2>Par difficulté</h2>")
        sections.append(f'<div class="card">{_heatmap(board, "by_difficulty", DIFFICULTIES)}</div>')
        sections.append("<h2>Par catégorie de question</h2>")
        sections.append(f'<div class="card">{_heatmap(board, "by_category", CATEGORIES)}</div>')
        sections.append(f"<h2>Détail des questions · {_e(config_label(best))}</h2>")
        sections.append(f'<div class="card">{_questions(board[0])}</div>')
        if best.get("warnings"):
            items = "".join(f"<li>{_e(w)}</li>" for w in best["warnings"])
            sections.append(f"<h2>Points d'attention</h2><ul>{items}</ul>")
    else:
        sections.append(
            "<p>Aucun run d'évaluation pour l'instant. Lancez <code>medsql eval</code>.</p>"
        )
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Text-to-SQL médicaments · Tableau de bord</title>
<style>{_CSS}</style></head>
<body><main>
<header>{LOGO_SVG}<h1>Text-to-SQL médicaments</h1></header>
<p class="sub">Banc d'évaluation de LLM locaux sur la Base de données publique des médicaments.</p>
{"".join(sections)}
<footer>Généré le {generated} par <code>medsql report</code>. Données : BDPM (ANSM), licence ouverte.</footer>
</main><div id="tip" role="tooltip"></div><script>{_JS}</script></body></html>
"""
