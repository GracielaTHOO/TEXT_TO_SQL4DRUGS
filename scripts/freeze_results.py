"""Fige les résultats d'une version : quels runs portent les chiffres publiés.

    python scripts/freeze_results.py 1.0.0

Écrit ``results/releases/v<version>.json`` : pour chaque configuration du classement (le run le
plus récent, comme le README et le tableau de bord) et pour chaque modèle du jeu adverse, le
fichier du run, son empreinte SHA-256 et ses chiffres clés. Les runs suivants peuvent changer
le classement ; ce fichier garde la trace de ce que la version annonçait.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from medsql import __version__
from medsql.eval.adversarial import load_red_teams
from medsql.eval.runner import load_runs
from medsql.eval.significance import run_ci
from medsql.report import config_label, latest_per_config, latest_red_teams

ROOT = Path(__file__).resolve().parents[1]


def _source(directory: Path, summary: dict[str, Any]) -> tuple[str, str]:
    """Retrouve le fichier d'un run par sa date de création et son modèle."""
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text("utf-8"))["summary"]
        if data["created_at"] == summary["created_at"] and data["model"] == summary["model"]:
            same_config = data.get("config") == summary.get("config")
            if same_config:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                return str(path.relative_to(ROOT)), digest
    raise FileNotFoundError(f"run introuvable : {summary['model']} {summary['created_at']}")


def freeze(version: str) -> dict[str, Any]:
    runs_dir, security_dir = ROOT / "results" / "runs", ROOT / "results" / "security"
    leaderboard = []
    for run in latest_per_config(load_runs(runs_dir)):
        s = run["summary"]
        path, digest = _source(runs_dir, s)
        low, high = run_ci(run["items"])
        leaderboard.append(
            {
                "configuration": config_label(s),
                "accuracy": s["accuracy"],
                "ci95": [round(low, 4), round(high, 4)],
                "n": s["n"],
                "abstention": s.get("abstention") or None,
                "latency_p50_s": s["latency_p50_s"],
                "created_at": s["created_at"],
                "file": path,
                "sha256": digest,
            }
        )
    security = []
    for run in latest_red_teams(load_red_teams(security_dir)):
        s = run["summary"]
        path, digest = _source(security_dir, s)
        security.append(
            {
                "model": s["model"],
                "n": s["n"],
                "tentatives_interdites": s["tentatives_interdites"],
                "incidents": s["incidents"],
                "base_intacte": s["base_intacte"],
                "created_at": s["created_at"],
                "file": path,
                "sha256": digest,
            }
        )
    return {
        "version": version,
        "frozen_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "package_version": __version__,
        "leaderboard": leaderboard,
        "security": security,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version", help="numéro de version, sans le v (ex. 1.0.0)")
    args = parser.parse_args()
    if args.version != __version__:
        parser.error(f"le paquet est en version {__version__}, pas {args.version}")
    out = ROOT / "results" / "releases" / f"v{args.version}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    frozen = freeze(args.version)
    out.write_text(json.dumps(frozen, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(
        f"{out.relative_to(ROOT)} : {len(frozen['leaderboard'])} configurations, "
        f"{len(frozen['security'])} modèles du jeu adverse"
    )


if __name__ == "__main__":
    main()
