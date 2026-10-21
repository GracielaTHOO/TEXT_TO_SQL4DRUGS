"""Rigueur statistique : intervalles de confiance et comparaison appariée de deux runs.

Avec 60 questions, une exactitude de 60 % a un intervalle de confiance à 95 % d'environ
±12 points : deux configurations ne se départagent qu'avec un test qui tient compte du fait
qu'elles répondent aux **mêmes** questions. D'où deux outils :

- ``bootstrap_ci`` : intervalle percentile par rééchantillonnage des questions (graine fixe,
  donc résultat reproductible) ;
- ``mcnemar`` : test exact de McNemar sur les questions discordantes (juste pour l'un, faux pour
  l'autre), p-valeur binomiale bilatérale. Les questions communes sont appariées par identifiant.

Tout est calculé à partir des réponses enregistrées dans les runs : rien n'est réexécuté.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

BOOTSTRAP_SAMPLES = 10_000
SEED = 20261021


def bootstrap_ci(
    outcomes: Sequence[bool],
    *,
    level: float = 0.95,
    samples: int = BOOTSTRAP_SAMPLES,
    seed: int = SEED,
) -> tuple[float, float]:
    """Intervalle de confiance percentile de la proportion de ``True``."""
    n = len(outcomes)
    if n == 0:
        return (0.0, 0.0)
    values = [1 if o else 0 for o in outcomes]
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(samples))
    tail = (1 - level) / 2
    lo = means[math.floor(tail * (samples - 1))]
    hi = means[math.ceil((1 - tail) * (samples - 1))]
    return (lo, hi)


def run_ci(items: Iterable[Mapping[str, Any]], **kwargs: Any) -> tuple[float, float]:
    return bootstrap_ci([bool(i["correct"]) for i in items], **kwargs)


@dataclass(frozen=True)
class McNemar:
    """Questions communes, discordances et p-valeur exacte bilatérale."""

    n: int
    only_a: int  # justes pour A seulement
    only_b: int  # justes pour B seulement
    p_value: float

    @property
    def significant(self) -> bool:
        return self.p_value < 0.05


def _binomial_two_sided(k: int, n: int) -> float:
    """P(X ≤ min(k, n−k)) × 2 pour X ~ B(n, 1/2), plafonnée à 1."""
    if n == 0:
        return 1.0
    low = min(k, n - k)
    tail: float = sum(math.comb(n, i) for i in range(low + 1)) / 2**n
    return min(1.0, 2 * tail)


def mcnemar(items_a: Iterable[Mapping[str, Any]], items_b: Iterable[Mapping[str, Any]]) -> McNemar:
    """Compare deux runs sur leurs questions communes (appariées par identifiant)."""
    a = {str(i["id"]): bool(i["correct"]) for i in items_a}
    b = {str(i["id"]): bool(i["correct"]) for i in items_b}
    common = sorted(a.keys() & b.keys())
    only_a = sum(a[q] and not b[q] for q in common)
    only_b = sum(b[q] and not a[q] for q in common)
    return McNemar(len(common), only_a, only_b, _binomial_two_sided(only_a, only_a + only_b))
