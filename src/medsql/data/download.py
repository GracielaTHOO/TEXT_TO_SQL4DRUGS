"""Téléchargement des fichiers bruts de la BDPM.

Source officielle : https://base-donnees-publique.medicaments.gouv.fr/telechargement
Licence : données publiques de l'ANSM, réutilisation libre (Licence Ouverte).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

from medsql.data.schema import SOURCE_FILES

logger = logging.getLogger(__name__)

BASE_URL = "https://base-donnees-publique.medicaments.gouv.fr"
# L'ANSM a changé de schéma d'URL ; on tente le plus récent puis l'historique.
URL_TEMPLATES = (
    BASE_URL + "/download/file/{name}",
    BASE_URL + "/telechargement.php?fichier={name}",
)
MANIFEST = "manifest.json"


@dataclass(frozen=True)
class DownloadedFile:
    name: str
    url: str
    bytes: int
    sha256: str


def _fetch(client: httpx.Client, name: str, retries: int) -> tuple[str, bytes]:
    last_error: Exception | None = None
    for template in URL_TEMPLATES:
        url = template.format(name=name)
        for attempt in range(1, retries + 1):
            try:
                response = client.get(url)
                response.raise_for_status()
                content = response.content
                # Une page HTML signifie une erreur côté serveur, pas un fichier de données.
                if content.lstrip()[:15].lower().startswith((b"<!doctype", b"<html")):
                    raise ValueError(f"réponse HTML inattendue pour {url}")
                return url, content
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                logger.warning("Échec %s (tentative %d/%d) : %s", url, attempt, retries, exc)
                time.sleep(min(2**attempt, 10))
    raise RuntimeError(f"Impossible de télécharger {name}") from last_error


def download_all(
    raw_dir: Path, *, retries: int = 3, timeout_s: float = 120
) -> list[DownloadedFile]:
    """Télécharge tous les fichiers sources et écrit un manifeste (URL, taille, SHA-256)."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    results: list[DownloadedFile] = []
    with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
        for name in SOURCE_FILES:
            url, content = _fetch(client, name, retries)
            (raw_dir / name).write_bytes(content)
            digest = hashlib.sha256(content).hexdigest()
            results.append(DownloadedFile(name, url, len(content), digest))
            logger.info("%s : %d octets", name, len(content))
    manifest = {
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": [asdict(r) for r in results],
    }
    (raw_dir / MANIFEST).write_text(json.dumps(manifest, indent=2, ensure_ascii=False), "utf-8")
    return results
