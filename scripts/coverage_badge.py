"""Badge de couverture des tests, sans service tiers.

    python scripts/coverage_badge.py coverage.xml assets/coverage.svg          # écrit le badge
    python scripts/coverage_badge.py coverage.xml assets/coverage.svg --check  # vérifie (CI)

La couverture combine lignes et branches, comme ``coverage report`` avec ``branch = true``.
La vérification tolère un point d'écart : les versions de Python ne comptent pas toutes les
branches de la même façon.
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

LABEL = "couverture"
COLOR = "#2a78d6"  # même bleu que les autres badges du README
CHAR_PX = 7  # largeur moyenne d'un caractère en Verdana 11 px
TOLERANCE = 1


def total_percent(report: Path) -> int:
    root = ET.parse(report).getroot()  # rapport produit par pytest-cov, fichier de confiance
    covered = int(root.get("lines-covered", 0)) + int(root.get("branches-covered", 0))
    valid = int(root.get("lines-valid", 0)) + int(root.get("branches-valid", 0))
    return round(100 * covered / valid) if valid else 0


def render(percent: int) -> str:
    value = f"{percent} %"
    left, right = 10 + CHAR_PX * len(LABEL), 10 + CHAR_PX * len(value)
    width = left + right
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" \
aria-label="{LABEL} : {value}"><title>{LABEL} : {value}</title>
<clipPath id="r"><rect width="{width}" height="20" rx="3"/></clipPath>
<g clip-path="url(#r)"><rect width="{left}" height="20" fill="#555"/>\
<rect x="{left}" width="{right}" height="20" fill="{COLOR}"/></g>
<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" \
font-size="11"><text x="{left / 2}" y="14">{LABEL}</text>\
<text x="{left + right / 2}" y="14">{value}</text></g>
<!-- couverture={percent} -->
</svg>
"""


def badge_percent(svg: Path) -> int | None:
    match = re.search(r"couverture=(\d+)", svg.read_text("utf-8")) if svg.exists() else None
    return int(match.group(1)) if match else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", type=Path, help="coverage.xml")
    parser.add_argument("badge", type=Path, help="fichier SVG du badge")
    parser.add_argument("--check", action="store_true", help="vérifier sans écrire")
    args = parser.parse_args(argv)
    percent = total_percent(args.report)
    if args.check:
        shown = badge_percent(args.badge)
        if shown is None or abs(shown - percent) > TOLERANCE:
            print(
                f"Badge à {shown} %, couverture mesurée {percent} % : lancer "
                f"`make coverage-badge` et committer {args.badge}.",
                file=sys.stderr,
            )
            return 1
        print(f"Badge à jour ({shown} %, mesuré {percent} %).")
        return 0
    args.badge.write_text(render(percent), "utf-8")
    print(f"{args.badge} : {percent} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
