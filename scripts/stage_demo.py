"""Assemble le contexte de construction de l'image Docker de la démo.

Copie le code, la licence et les runs d'évaluation à côté du Dockerfile de ``docker/``.
Utilisé par ``.github/workflows/demo-image.yml`` ; en local :

    python scripts/stage_demo.py --out build/demo
    docker build -t medsql-demo build/demo
    docker run -p 7860:7860 medsql-demo    # http://127.0.0.1:7860
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = ("pyproject.toml", "LICENSE", "src", "app", "results/runs")


def stage(target: Path) -> None:
    for name in INCLUDE:
        src = ROOT / name
        if not src.exists():
            continue
        dst = target / name
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    for name in ("Dockerfile", "start.sh", "README.md"):
        shutil.copy2(ROOT / "docker" / name, target / name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path, required=True, help="dossier à créer (écrasé s'il existe)"
    )
    args = parser.parse_args()
    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)
    stage(args.out)
    print(args.out)


if __name__ == "__main__":
    main()
