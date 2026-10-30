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

from medsql.eval.abstention import abstention_stats
from medsql.eval.dataset import CATEGORIES, DIFFICULTIES
from medsql.eval.errors import ERROR_TYPES, error_breakdown
from medsql.eval.robustness import robustness
from medsql.eval.significance import McNemar, mcnemar, run_ci
from medsql.models import model_info

README_START = "<!-- RESULTS:START -->"
README_END = "<!-- RESULTS:END -->"

Run = dict[str, Any]

LABELS = {
    "facile": "Facile",
    "moyen": "Moyen",
    "difficile": "Difficile",
    "comptage": "Comptage",
    "filtrage": "Filtrage",
    "jointure": "Jointures",
    "agregation": "Agrégations",
    "classement": "Classements (top N)",
    "dates": "Dates",
    "prix": "Prix et remboursement",
    "generiques": "Génériques",
    "has": "Avis HAS",
    "disponibilite": "Ruptures de stock",
    "hors_perimetre": "Hors périmètre (abstention)",
}


# --------------------------------------------------------------------------- sélection


def config_label(summary: dict[str, Any]) -> str:
    cfg = summary.get("config", {})
    parts = [str(summary["model"])]
    if not cfg.get("few_shot", True):
        parts.append("zero-shot")
    if cfg.get("max_repairs", 1) == 0:
        parts.append("sans auto-correction")
    # Les runs antérieurs à l'option n'ont pas la clé : ils ont été faits sans libellés.
    if not cfg.get("value_hints", False):
        parts.append("sans libellés exacts")
    if _is_dynamic(summary):
        parts.append(f"exemples dynamiques ({cfg.get('embedder', '?')})")
    return " · ".join(parts)


def _is_dynamic(summary: dict[str, Any]) -> bool:
    return bool(summary.get("config", {}).get("examples") == "dynamiques")


def latest_per_config(runs: Sequence[Run]) -> list[Run]:
    """Dernier run complet de chaque configuration, du meilleur au moins bon."""
    latest: dict[str, Run] = {}
    for run in runs:  # runs triés du plus ancien au plus récent
        s = run["summary"]
        if s.get("config", {}).get("limit"):
            continue  # les runs partiels (--limit) ne vont pas au classement
        latest[config_label(s)] = run
    return sorted(latest.values(), key=lambda r: -float(r["summary"]["accuracy"]))


# Les trois facteurs d'ablation : (clé, libellé de la variante qui le retire).
FACTORS: tuple[tuple[str, str], ...] = (
    ("few_shot", "zero-shot"),
    ("repairs", "sans auto-correction"),
    ("value_hints", "sans libellés exacts"),
)


def _factors(summary: dict[str, Any]) -> dict[str, bool]:
    cfg = summary.get("config", {})
    return {
        "few_shot": bool(cfg.get("few_shot", True)),
        "repairs": cfg.get("max_repairs", 1) != 0,
        # Les runs antérieurs à l'option n'ont pas la clé : ils ont été faits sans libellés.
        "value_hints": bool(cfg.get("value_hints", False)),
    }


def _is_baseline(summary: dict[str, Any]) -> bool:
    return all(_factors(summary).values()) and not _is_dynamic(summary)


def _variant(summary: dict[str, Any]) -> str:
    return config_label(summary).removeprefix(str(summary["model"])).removeprefix(" · ") or "base"


def ablations(board: Sequence[Run]) -> list[tuple[str, str, str, float, float, float]]:
    """Effet de chaque facteur retiré seul, toutes choses égales par ailleurs.

    Pour chaque run, et chaque facteur absent de sa configuration, cherche le run du même
    modèle qui ne diffère que par ce facteur. Renvoie (modèle, facteur retiré, configuration
    de référence, exactitude, écart en points, p-valeur de McNemar).
    """
    # Les runs à exemples dynamiques ont leur propre comparaison (dynamic_examples).
    board = [r for r in board if not _is_dynamic(r["summary"])]
    by_key = {(r["summary"]["model"], tuple(_factors(r["summary"]).values())): r for r in board}
    rows = []
    for run in board:
        s = run["summary"]
        factors = _factors(s)
        for key, removed in FACTORS:
            if factors[key]:
                continue
            ref_key = tuple(v or k == key for k, v in factors.items())
            ref_run = by_key.get((s["model"], ref_key))
            if ref_run is None:
                continue
            ref = ref_run["summary"]
            acc = float(s["accuracy"])
            delta = 100 * (acc - float(ref["accuracy"]))
            p = mcnemar(run["items"], ref_run["items"]).p_value
            rows.append((str(s["model"]), removed, _variant(ref), acc, delta, p))
    return sorted(rows, key=lambda r: (r[0], r[2] != "base", -r[4]))


# --------------------------------------------------------------------------- README


def _pct(x: float) -> str:
    return f"{100 * x:.1f} %".replace(".", ",")


def _ci(run: Run) -> str:
    lo, hi = run_ci(run["items"])
    return f"{100 * lo:.1f} – {100 * hi:.1f} %".replace(".", ",")


def _abstention(run: Run) -> str:
    stats = abstention_stats(run["items"])
    if not stats:
        return "–"
    return f"{stats['correct']:.0f}/{stats['out_of_scope']:.0f}"


def _p(p: float) -> str:
    return ("< 0,001" if p < 0.001 else f"{p:.3f}".replace(".", ",")) + (" ✱" if p < 0.05 else "")


# Au-delà, toutes les paires noieraient le tableau : on compare chaque run au meilleur.
MAX_ALL_PAIRS = 4


def pairwise(runs: Sequence[Run]) -> list[tuple[str, str, McNemar]]:
    """Test de McNemar pour chaque paire de runs (du meilleur au moins bon).

    Au-delà de ``MAX_ALL_PAIRS`` runs, seul le premier (le meilleur) est comparé aux autres.
    """
    pairs = (
        [(a, b) for i, a in enumerate(runs) for b in runs[i + 1 :]]
        if len(runs) <= MAX_ALL_PAIRS
        else [(runs[0], b) for b in runs[1:]]
    )
    return [
        (config_label(a["summary"]), config_label(b["summary"]), mcnemar(a["items"], b["items"]))
        for a, b in pairs
    ]


def _sec(x: float) -> str:
    return f"{x:.1f} s".replace(".", ",")


def readme_table(runs: Sequence[Run]) -> str:
    board = latest_per_config(runs)
    if not board:
        return "_Aucun run d'évaluation complet pour l'instant. Lancez `medsql eval`._"
    lines = [
        "| Modèle | Exactitude | IC 95 % | Exactitude stricte | SQL exécutable | Abstention | Latence p50 | Latence p95 | Date |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in board:
        s = run["summary"]
        lines.append(
            f"| {config_label(s)} | **{_pct(s['accuracy'])}** | {_ci(run)} | {_pct(s['accuracy_strict'])} "
            f"| {_pct(s['executable_rate'])} | {_abstention(run)} | {_sec(s['latency_p50_s'])} "
            f"| {_sec(s['latency_p95_s'])} | {s['created_at'][:10]} |"
        )
    stats = abstention_stats(board[0]["items"])
    n = board[0]["summary"]["n"] - int(stats.get("out_of_scope", 0))
    outside = f" + {stats['out_of_scope']:.0f} hors périmètre" if stats else ""
    lines.append("")
    lines.append(
        f"_{n} questions{outside} · exactitude = résultat d'exécution identique à la référence, "
        "sur les questions du périmètre · abstention = questions hors périmètre correctement "
        "refusées · IC 95 % par bootstrap sur les questions "
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
td.heat{border:2px solid var(--surface);border-radius:6px}
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


def _bar_chart(rows: list[tuple[str, float, float, float]]) -> str:
    """Barres horizontales (une série) : exactitude par configuration, avec son IC 95 %."""
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
    for i, (name, acc, lo, hi) in enumerate(rows):
        y = i * row_h + 6
        w = max(acc * bar_w, 2)
        x_lo, x_hi = label_w + lo * bar_w, label_w + hi * bar_w
        tip = f"{name} : {_pct(acc)} (IC 95 % {_pct(lo)} – {_pct(hi)})"
        parts.append(f'<text x="{label_w - 10}" y="{y + 16}" text-anchor="end">{_e(name)}</text>')
        parts.append(
            f'<rect x="{label_w}" y="{y + 3}" width="{w:.1f}" height="18" rx="4" fill="var(--accent)" '
            f'data-tip="{_e(tip)}"/>'
        )
        # Moustache de l'intervalle de confiance, par-dessus la barre.
        parts.append(
            f'<path d="M{x_lo:.1f} {y + 12}H{x_hi:.1f}M{x_lo:.1f} {y + 7}V{y + 17}M{x_hi:.1f} {y + 7}V{y + 17}" '
            'stroke="var(--ink)" stroke-width="1.5" fill="none"/>'
        )
        parts.append(
            f'<text class="val" x="{max(label_w + w, x_hi) + 8:.1f}" y="{y + 16}">{_pct(acc)}</text>'
        )
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
            tip = f"{config_label(run['summary'])} · {LABELS.get(name, name)} : {_pct(stat['accuracy'])} sur {stat['n']} questions"
            cells.append(
                f'<td class="n heat" style="background:{bg};color:{fg}" data-tip="{_e(tip)}">'
                f"{_pct(stat['accuracy'])}</td>"
            )
        body.append(f"<tr><th>{_e(LABELS.get(name, name))}</th>{''.join(cells)}</tr>")
    return f"<table><thead><tr><th></th>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _leaderboard(board: list[Run]) -> str:
    rows = []
    for rank, run in enumerate(board, 1):
        s = run["summary"]
        rows.append(
            f"<tr><td class='n'>{rank}</td><td>{_e(config_label(s))}</td><td>{_e(s['backend'])}</td>"
            f"<td class='n'><b>{_pct(s['accuracy'])}</b></td><td class='n'>{_ci(run)}</td>"
            f"<td class='n'>{_pct(s['accuracy_strict'])}</td>"
            f"<td class='n'>{_pct(s['executable_rate'])}</td><td class='n'>{s['repaired']}</td>"
            f"<td class='n'>{_sec(s['latency_p50_s'])}</td><td class='n'>{_sec(s['latency_p95_s'])}</td>"
            f"<td class='n'>{s['tokens_per_question']:.0f}</td><td>{_e(s['created_at'][:10])}</td></tr>"
        )
    return (
        "<table><thead><tr><th class='n'>#</th><th>Configuration</th><th>Backend</th>"
        "<th class='n'>Exactitude</th><th class='n'>IC 95 %</th><th class='n'>Stricte</th>"
        "<th class='n'>Exécutable</th>"
        "<th class='n'>Réparées</th><th class='n'>p50</th><th class='n'>p95</th>"
        "<th class='n'>Tokens/question</th><th>Date</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def dynamic_examples(board: Sequence[Run]) -> list[tuple[str, str, float, float, float, float]]:
    """Exemples dynamiques contre exemples fixes, pour chaque modèle et chaque encodeur.

    Renvoie (modèle, encodeur, exactitude fixes, exactitude dynamiques, écart en points,
    p-valeur de McNemar), en comparant à la configuration par défaut du même modèle.
    """
    fixed = {r["summary"]["model"]: r for r in board if _is_baseline(r["summary"])}
    rows = []
    for run in board:
        s = run["summary"]
        cfg = s.get("config", {})
        ref = fixed.get(s["model"])
        if not _is_dynamic(s) or ref is None or not all(_factors(s).values()):
            continue
        acc, ref_acc = float(s["accuracy"]), float(ref["summary"]["accuracy"])
        p = mcnemar(run["items"], ref["items"]).p_value
        rows.append(
            (str(s["model"]), str(cfg.get("embedder", "?")), ref_acc, acc, 100 * (acc - ref_acc), p)
        )
    return sorted(rows)


def _dynamic_table(rows: list[tuple[str, str, float, float, float, float]]) -> str:
    body = []
    for model, embedder, ref_acc, acc, delta, p in rows:
        cls = "ok" if delta > 0 else "ko" if delta < 0 else ""
        points = f"{'+' if delta > 0 else ''}{delta:.1f}".replace(".", ",")
        body.append(
            f"<tr><td>{_e(model)}</td><td>{_e(embedder)}</td><td class='n'>{_pct(ref_acc)}</td>"
            f"<td class='n'>{_pct(acc)}</td><td class='n'><span class='{cls}'>{points} pt</span></td>"
            f"<td class='n'>{_p(p)}</td></tr>"
        )
    return (
        "<table><thead><tr><th>Modèle</th><th>Encodeur</th><th class='n'>Exemples fixes</th>"
        "<th class='n'>Exemples dynamiques</th><th class='n'>Écart</th>"
        f"<th class='n'>p (McNemar)</th></tr></thead><tbody>{''.join(body)}</tbody></table>"
    )


def _families_table(runs: Sequence[Run]) -> str:
    """Comparaison multi-familles : un run par modèle catalogué, du meilleur au moins bon."""
    rows = []
    for run in runs:
        s = run["summary"]
        info = model_info(str(s["model"]))
        if info is None:
            continue
        size = f"{info.params_b:g}".replace(".", ",")
        rows.append(
            f"<tr><td>{_e(s['model'])}</td><td>{_e(info.family)}</td><td>{_e(info.publisher)}</td>"
            f"<td class='n'>{size} Md</td><td>{_e(info.specialty)}</td>"
            f"<td class='n'><b>{_pct(s['accuracy'])}</b></td><td class='n'>{_ci(run)}</td>"
            f"<td class='n'>{_abstention(run)}</td><td class='n'>{_sec(s['latency_p50_s'])}</td>"
            f"<td>{_e(info.licence)}</td></tr>"
        )
    if len(rows) < 2:
        return ""
    return (
        "<table><thead><tr><th>Modèle</th><th>Famille</th><th>Éditeur</th>"
        "<th class='n'>Paramètres</th><th>Spécialité</th><th class='n'>Exactitude</th>"
        "<th class='n'>IC 95 %</th><th class='n'>Abstention</th><th class='n'>p50</th>"
        f"<th>Licence</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


def _ablation_table(rows: list[tuple[str, str, str, float, float, float]]) -> str:
    body = []
    for model, removed, reference, acc, delta, p in rows:
        cls = "ok" if delta > 0 else "ko" if delta < 0 else ""
        points = f"{'+' if delta > 0 else ''}{delta:.1f}".replace(".", ",")
        body.append(
            f"<tr><td>{_e(model)}</td><td>{_e(removed)}</td><td>{_e(reference)}</td>"
            f"<td class='n'>{_pct(acc)}</td><td class='n'><span class='{cls}'>{points} pt</span></td>"
            f"<td class='n'>{_p(p)}</td></tr>"
        )
    return (
        "<table><thead><tr><th>Modèle</th><th>Facteur retiré</th><th>Par rapport à</th>"
        "<th class='n'>Exactitude</th><th class='n'>Écart</th><th class='n'>p (McNemar)</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
    )


def _pairwise_table(rows: list[tuple[str, str, McNemar]]) -> str:
    body = "".join(
        f"<tr><td>{_e(a)}</td><td>{_e(b)}</td><td class='n'>{m.n}</td><td class='n'>{m.only_a}</td>"
        f"<td class='n'>{m.only_b}</td><td class='n'>{_p(m.p_value)}</td>"
        f"<td>{'écart significatif' if m.significant else 'non significatif'}</td></tr>"
        for a, b, m in rows
    )
    return (
        "<table><thead><tr><th>A</th><th>B</th><th class='n'>Questions communes</th>"
        "<th class='n'>Justes pour A seul</th><th class='n'>Justes pour B seul</th>"
        "<th class='n'>p (McNemar)</th><th>Conclusion au seuil de 5 %</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def _robustness_table(runs: Sequence[Run]) -> str:
    rows = []
    for run in runs:
        r = robustness(run["items"])
        if not r:
            continue
        rows.append(
            f"<tr><td>{_e(config_label(run['summary']))}</td><td class='n'>{r['pairs']:.0f}</td>"
            f"<td class='n'>{r['both']:.0f}</td><td class='n'>{r['only_original']:.0f}</td>"
            f"<td class='n'>{r['only_paraphrase']:.0f}</td><td class='n'>{r['neither']:.0f}</td>"
            f"<td class='n'><b>{_pct(r['consistency'])}</b></td><td class='n'>{_pct(r['kept'])}</td></tr>"
        )
    if not rows:
        return ""
    return (
        "<table><thead><tr><th>Configuration</th><th class='n'>Paires</th>"
        "<th class='n'>Justes les deux</th><th class='n'>Source seule</th>"
        "<th class='n'>Reformulation seule</th><th class='n'>Fausses les deux</th>"
        "<th class='n'>Cohérence</th><th class='n'>Justes conservées</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _abstention_table(runs: Sequence[Run]) -> str:
    rows = []
    for run in runs:
        a = abstention_stats(run["items"])
        if not a:
            continue
        rows.append(
            f"<tr><td>{_e(config_label(run['summary']))}</td>"
            f"<td class='n'><b>{a['correct']:.0f}/{a['out_of_scope']:.0f}</b></td>"
            f"<td class='n'>{_pct(a['rate'])}</td>"
            f"<td class='n'>{a['false_abstentions']:.0f}/{a['in_scope']:.0f}</td>"
            f"<td class='n'>{_pct(a['false_rate'])}</td></tr>"
        )
    if not rows:
        return ""
    return (
        "<table><thead><tr><th>Configuration</th><th class='n'>Abstentions correctes</th>"
        "<th class='n'>Taux</th><th class='n'>Abstentions à tort</th><th class='n'>Taux</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


def _error_table(runs: Sequence[Run]) -> str:
    """Causes des réponses fausses (lignes) pour chaque configuration (colonnes)."""
    breakdowns = [error_breakdown(r["items"]) for r in runs]
    head = "".join(f'<th class="n">{_e(config_label(r["summary"]))}</th>' for r in runs)
    body = []
    for key, label in ERROR_TYPES:
        if not any(key in b for b in breakdowns):
            continue
        cells = []
        for run, found in zip(runs, breakdowns, strict=True):
            ids = found.get(key, [])
            if not ids:
                cells.append('<td class="n">–</td>')
                continue
            tip = f"{config_label(run['summary'])} · {label} : {', '.join(ids)}"
            cells.append(f'<td class="n" data-tip="{_e(tip)}">{len(ids)}</td>')
        body.append(f"<tr><th>{_e(label)}</th>{''.join(cells)}</tr>")
    totals = "".join(
        f'<td class="n"><b>{sum(len(v) for v in b.values())}</b></td>' for b in breakdowns
    )
    body.append(f"<tr><th>Total des réponses fausses</th>{totals}</tr>")
    return f"<table><thead><tr><th></th>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _questions(run: Run) -> str:
    rows = []
    for item in run["items"]:
        mark = (
            '<span class="ok">✓ juste</span>'
            if item["correct"]
            else '<span class="ko">✗ faux</span>'
        )
        generated = "abstention" if item.get("abstained") else item["pred_sql"] or "—"
        reference = "abstention attendue" if item.get("hors_perimetre") else item["gold_sql"]
        detail = (
            f"<details><summary>SQL</summary><p><b>Généré</b></p><code>{_e(generated)}</code>"
            f"<p><b>Référence</b></p><code>{_e(reference)}</code>"
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


def _comparison_sections(baselines: Sequence[Run]) -> list[str]:
    """Sections « Familles de modèles » et « Les écarts sont-ils réels ? »."""
    sections: list[str] = []
    families = _families_table(baselines)
    if families:
        sections.append("<h2>Familles de modèles</h2>")
        sections.append(
            "<p class='note'>Configuration par défaut pour chaque modèle, quantifié en 4 bits et "
            "servi par Ollama sur le même processeur. Spécialité : entraînement généraliste, "
            "orienté code ou dédié au SQL.</p>"
        )
        sections.append(f'<div class="card">{families}</div>')
    if len(baselines) > 1:
        sections.append("<h2>Les écarts sont-ils réels ?</h2>")
        vs_best = (
            " Avec plus de quatre modèles, chacun est comparé au meilleur."
            if len(baselines) > MAX_ALL_PAIRS
            else ""
        )
        sections.append(
            "<p class='note'>Test exact de McNemar sur les questions communes : seules comptent "
            "celles où un modèle a juste et l'autre faux. ✱ = significatif au seuil de 5 %."
            f"{vs_best}</p>"
        )
        sections.append(f'<div class="card">{_pairwise_table(pairwise(baselines))}</div>')
    return sections


def _variant_sections(board: Sequence[Run]) -> list[str]:
    """Sections « Exemples choisis par similarité » et « Ablations »."""
    sections: list[str] = []
    dynamic = dynamic_examples(board)
    if dynamic:
        sections.append("<h2>Exemples choisis par similarité</h2>")
        sections.append(
            "<p class='note'>Les trois exemples fixes du prompt sont remplacés, pour chaque "
            "question, par les trois exemples les plus proches d'une réserve de 32 exemples "
            "disjointe du jeu d'évaluation. L'exemple d'abstention reste. p : test de McNemar "
            "apparié contre la configuration par défaut du même modèle.</p>"
        )
        sections.append(f'<div class="card">{_dynamic_table(dynamic)}</div>')
    deltas = ablations(board)
    if deltas:
        sections.append("<h2>Ablations</h2>")
        sections.append(
            "<p class='note'>Effet de chaque facteur retiré seul, par rapport au run du même modèle "
            "qui ne diffère que par ce facteur, en points d'exactitude. La base combine exemples "
            "few-shot, une auto-correction et libellés exacts ; p : test de McNemar apparié.</p>"
        )
        sections.append(f'<div class="card">{_ablation_table(deltas)}</div>')
    return sections


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
        bars = [
            (config_label(r["summary"]), float(r["summary"]["accuracy"]), *run_ci(r["items"]))
            for r in board
        ]
        sections.append(f'<div class="card">{_bar_chart(bars)}</div>')
        sections.append("<h2>Classement détaillé</h2>")
        sections.append(f'<div class="card">{_leaderboard(board)}</div>')
        baselines = [r for r in board if _is_baseline(r["summary"])] or board[:3]
        sections.extend(_comparison_sections(baselines))
        sections.extend(_variant_sections(board))
        sections.append("<h2>Par difficulté</h2>")
        sections.append(f'<div class="card">{_heatmap(board, "by_difficulty", DIFFICULTIES)}</div>')
        sections.append("<h2>Par catégorie de question</h2>")
        sections.append(f'<div class="card">{_heatmap(board, "by_category", CATEGORIES)}</div>')
        robust = _robustness_table(baselines)
        if robust:
            sections.append("<h2>Robustesse à la formulation</h2>")
            sections.append(
                "<p class='note'>Chaque reformulation partage la requête de référence de sa question "
                "source. Cohérence : les deux formulations ont le même sort. Justes conservées : part "
                "des sources justes dont la reformulation reste juste.</p>"
            )
            sections.append(f'<div class="card">{robust}</div>')
        abstain = _abstention_table(baselines)
        if abstain:
            sections.append("<h2>Savoir s'abstenir</h2>")
            sections.append(
                "<p class='note'>Questions sans réponse dans la base (posologie, ventes, demande de "
                "modification…) : la seule bonne réponse est de refuser. Une abstention à tort refuse "
                "une question à laquelle la base répond. L'exactitude des autres sections ne porte "
                "que sur les questions du périmètre.</p>"
            )
            sections.append(f'<div class="card">{abstain}</div>')
        sections.append("<h2>Analyse des erreurs</h2>")
        sections.append(
            "<p class='note'>Une cause par réponse fausse, la première qui s'applique de haut en bas "
            "(comparaison automatique avec la requête de référence). Survoler un nombre pour voir "
            "les questions.</p>"
        )
        sections.append(f'<div class="card">{_error_table(baselines)}</div>')
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
