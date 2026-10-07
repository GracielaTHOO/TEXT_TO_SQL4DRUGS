"""Publie la démo sur Hugging Face Spaces.

Assemble un dossier temporaire (Dockerfile, code, résultats d'évaluation) puis l'envoie
sur le Space avec ``huggingface_hub``. Utilisé par ``.github/workflows/deploy-space.yml``.

Usage : HF_TOKEN=... python scripts/deploy_space.py --space GracielaTHOO/text2sql-medicaments
"""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

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
        shutil.copy2(ROOT / "space" / name, target / name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--space", required=True, help="identifiant du Space (owner/nom)")
    args = parser.parse_args()
    api = HfApi(token=os.environ["HF_TOKEN"])
    api.create_repo(args.space, repo_type="space", space_sdk="docker", exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        stage(Path(tmp))
        api.upload_folder(
            folder_path=tmp,
            repo_id=args.space,
            repo_type="space",
            commit_message="Déploiement depuis GitHub Actions",
            delete_patterns=["src/**", "app/**", "results/**"],
        )
    print(f"https://huggingface.co/spaces/{args.space}")


if __name__ == "__main__":
    main()
