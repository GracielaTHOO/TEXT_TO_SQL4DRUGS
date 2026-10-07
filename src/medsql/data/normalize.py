"""Fonctions de normalisation des champs bruts de la BDPM.

Les fichiers de l'ANSM présentent plusieurs particularités qu'il faut traiter avec soin :
- encodage historique Windows-1252 (parfois UTF-8 selon les millésimes) ;
- trois formats de date (``JJ/MM/AAAA``, ``AAAAMMJJ``, ``AAAA-MM-JJ``) ;
- prix à virgule décimale, parfois avec une virgule comme séparateur de milliers
  (``1,086,58`` signifie 1086,58 €) ;
- taux de remboursement libres (``65%``, ``65 %``, ``100%``) ;
- espaces parasites en début et fin de champ.
"""

from __future__ import annotations

import re
from datetime import date

_DATE_PATTERNS: tuple[tuple[re.Pattern[str], tuple[int, int, int]], ...] = (
    (re.compile(r"^(\d{2})/(\d{2})/(\d{4})$"), (3, 2, 1)),
    (re.compile(r"^(\d{4})(\d{2})(\d{2})$"), (1, 2, 3)),
    (re.compile(r"^(\d{4})-(\d{2})-(\d{2})$"), (1, 2, 3)),
)

_GENERIC_TYPES = {
    0: "princeps",
    1: "générique",
    2: "génériques par complémentarité posologique",
    4: "générique substituable",
}


def decode(raw: bytes) -> str:
    """Décode un fichier BDPM : UTF-8 strict si possible, sinon Windows-1252."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
    return text.lstrip("﻿")


def clean(value: str | None) -> str | None:
    """Supprime les espaces parasites ; une chaîne vide devient ``None``."""
    if value is None:
        return None
    value = value.replace("\xa0", " ").strip()
    return value or None


def parse_date(value: str | None) -> str | None:
    """Convertit une date BDPM en ISO 8601 (``AAAA-MM-JJ``), ``None`` si invalide."""
    value = clean(value)
    if value is None:
        return None
    for pattern, (y, m, d) in _DATE_PATTERNS:
        match = pattern.match(value)
        if match:
            try:
                return date(int(match[y]), int(match[m]), int(match[d])).isoformat()
            except ValueError:
                return None
    return None


def parse_price(value: str | None) -> float | None:
    """Convertit un prix BDPM en ``float`` (euros).

    >>> parse_price("2,18")
    2.18
    >>> parse_price("1,086,58")
    1086.58
    >>> parse_price("1 086,58")
    1086.58
    """
    value = clean(value)
    if value is None:
        return None
    value = value.replace(" ", "").replace("€", "")
    if "," in value:
        integer, _, decimals = value.rpartition(",")
        value = integer.replace(",", "").replace(".", "") + "." + decimals
    try:
        return round(float(value), 2)
    except ValueError:
        return None


def parse_rate(value: str | None) -> int | None:
    """Extrait le taux de remboursement en pourcentage entier (``'65 %'`` → 65)."""
    value = clean(value)
    if value is None:
        return None
    match = re.search(r"\d+", value)
    return int(match.group()) if match else None


def parse_bool(value: str | None) -> int | None:
    """``oui``/``non`` → 1/0 (SQLite n'a pas de type booléen natif)."""
    value = clean(value)
    if value is None:
        return None
    lowered = value.lower()
    if lowered in {"oui", "o", "true", "1"}:
        return 1
    if lowered in {"non", "n", "false", "0"}:
        return 0
    return None


def parse_int(value: str | None) -> int | None:
    value = clean(value)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def generic_label(code: int | None) -> str | None:
    return _GENERIC_TYPES.get(code) if code is not None else None


def split_routes(value: str | None) -> list[str]:
    """Éclate ``'orale;sublinguale'`` en ``['orale', 'sublinguale']`` (sans doublons)."""
    value = clean(value)
    if value is None:
        return []
    routes = (clean(v) for v in value.split(";"))
    return list(dict.fromkeys(r.lower() for r in routes if r))
