"""Captures d'écran et GIF animé de la démo, sur une démo qui tourne déjà.

    python scripts/capture_demo.py --url http://127.0.0.1:7860 --out assets/demo

Pose chaque question comme un visiteur (saisie au clavier, clic sur le bouton), attend la réponse
du modèle, enregistre une capture PNG par question et assemble un GIF de l'ensemble. Le workflow
*Captures de la démo* le lance sur l'image Docker, avec la vraie BDPM et le vrai modèle : les
captures montrent donc des réponses réelles, jamais mises en scène.

Dépendances (hors projet) : ``pip install playwright pillow`` puis ``playwright install chromium``.
"""

from __future__ import annotations

import argparse
import io
import time
from pathlib import Path
from typing import Any

from PIL import Image
from playwright.sync_api import Page, sync_playwright

QUESTIONS = (
    "Combien de médicaments sont actuellement commercialisés ?",
    "Quelles sont les 5 substances actives présentes dans le plus de spécialités ?",
    "Quelle est la posologie de l'amoxicilline chez l'adulte ?",  # abstention attendue
)
VIEWPORT = {"width": 1280, "height": 900}
GIF_WIDTH = 960
FRAME_EVERY_S = 0.6
HOLD_FRAMES = 6  # images répétées sur la réponse, pour laisser le temps de la lire
ANSWER_TIMEOUT_S = 240
DONE_MARKS = ("✅", "⊘", "❌")


def _frame(page: Page) -> Image.Image:
    shot = Image.open(io.BytesIO(page.screenshot()))
    ratio = GIF_WIDTH / shot.width
    return shot.convert("RGB").resize((GIF_WIDTH, round(shot.height * ratio)), Image.LANCZOS)


def _status(page: Page) -> str:
    text: Any = page.evaluate("() => document.querySelector('#status')?.innerText ?? ''")
    return str(text).strip()


def ask(page: Page, question: str, frames: list[Image.Image]) -> str:
    """Saisit la question, clique, et capture jusqu'à la réponse ; renvoie le statut affiché."""
    before = _status(page)
    box = page.get_by_label("Votre question")
    box.fill("")
    for k, char in enumerate(question):
        box.type(char, delay=25)
        if k % 6 == 0:
            frames.append(_frame(page))
    page.get_by_role("button", name="Interroger la base").click()
    deadline = time.monotonic() + ANSWER_TIMEOUT_S
    while time.monotonic() < deadline:
        time.sleep(FRAME_EVERY_S)
        frames.append(_frame(page))
        status = _status(page)
        busy = "processing" in status.lower()  # surimpression de Gradio pendant le calcul
        if not busy and status != before and any(mark in status for mark in DONE_MARKS):
            time.sleep(1.0)  # rendu du tableau et de la phrase
            final = _frame(page)
            frames.extend([final] * HOLD_FRAMES)
            return status
    raise TimeoutError(f"pas de réponse en {ANSWER_TIMEOUT_S} s : {question}")


def save_gif(frames: list[Image.Image], path: Path) -> None:
    # Palette commune calculée sur une image représentative : couleurs stables d'une image à
    # l'autre, fichier plus léger.
    palette = frames[-1].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    images = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    images[0].save(
        path,
        save_all=True,
        append_images=images[1:],
        duration=int(FRAME_EVERY_S * 1000),
        loop=0,
        optimize=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://127.0.0.1:7860")
    parser.add_argument("--out", type=Path, default=Path("assets/demo"))
    parser.add_argument("--executable", help="navigateur Chromium à utiliser (facultatif)")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    frames: list[Image.Image] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.executable)
        page = browser.new_page(viewport=VIEWPORT)  # type: ignore[arg-type]
        page.goto(args.url, wait_until="domcontentloaded")  # Gradio garde des connexions ouvertes
        page.get_by_label("Votre question").wait_for(timeout=120_000)
        page.screenshot(path=str(args.out / "accueil.png"))
        for k, question in enumerate(QUESTIONS, start=1):
            status = ask(page, question, frames)
            page.screenshot(path=str(args.out / f"question-{k}.png"), full_page=True)
            print(f"{k}. {question}\n   {status.splitlines()[0] if status else ''}")
        page.get_by_role("tab", name="Évaluation").click()
        time.sleep(2)
        page.screenshot(path=str(args.out / "evaluation.png"))
        browser.close()
    save_gif(frames, args.out / "demo.gif")
    size = (args.out / "demo.gif").stat().st_size / 1e6
    print(f"{len(frames)} images, demo.gif : {size:.1f} Mo")


if __name__ == "__main__":
    main()
