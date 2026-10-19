"""Publie la démo sur Hugging Face Spaces.

Assemble un dossier temporaire (Dockerfile, code, résultats d'évaluation) puis l'envoie
sur le Space avec ``huggingface_hub``. Utilisé par ``.github/workflows/deploy-space.yml``.

Usage : HF_TOKEN=... python scripts/deploy_space.py --space GracielaTHOO/text2sql-medicaments
        python scripts/deploy_space.py --out build/space   # assemble seulement (test de l'image)
"""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
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
        shutil.copy2(ROOT / "space" / name, target / name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--space", help="identifiant du Space (owner/nom)")
    target.add_argument("--out", type=Path, help="dossier où assembler le Space, sans le publier")
    args = parser.parse_args()
    if args.out:
        if args.out.exists():
            shutil.rmtree(args.out)
        args.out.mkdir(parents=True)
        stage(args.out)
        print(args.out)
        return
    from huggingface_hub import HfApi  # noqa: PLC0415 (inutile pour assembler)

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
