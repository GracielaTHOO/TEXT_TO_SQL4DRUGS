"""Indicateurs de performance d'un run (S12) : premier token, débits, coût CPU.

- **Temps de premier token** (TTFT) : chargement du modèle + lecture du prompt, au premier
  appel de chaque question. C'est l'attente avant que la réponse commence.
- **Débit de génération** : tokens produits / temps de génération pure, sur tout le run.
- **Débit de lecture du prompt** : tokens du prompt / temps de lecture, tels que les rapporte
  Ollama. Quand le préfixe commun (règles, schéma, exemples) est repris d'une question à
  l'autre, ce débit est apparent : à comparer entre modèles, pas à lire comme une vitesse brute.
- **CPU par question** : secondes de processeur consommées par la machine (tous cœurs).

Les runs antérieurs à S12, ou servis par une API compatible OpenAI, n'ont pas ces durées :
le bilan est alors vide.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping
from typing import Any


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    k = (len(ordered) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def performance(items: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    rows = list(items)
    ttft = [float(i["ttft_s"]) for i in rows if i.get("ttft_s") is not None]
    if not ttft:
        return {}
    result: dict[str, float] = {
        "ttft_p50_s": round(_percentile(ttft, 0.5), 3),
        "ttft_p95_s": round(_percentile(ttft, 0.95), 3),
    }
    eval_s = sum(float(i.get("eval_s") or 0) for i in rows)
    if eval_s > 0:
        generated = sum(int(i.get("completion_tokens") or 0) for i in rows)
        result["generation_tokens_per_s"] = round(generated / eval_s, 1)
    prompt_s = sum(float(i.get("prompt_eval_s") or 0) for i in rows)
    if prompt_s > 0:
        read = sum(int(i.get("prompt_tokens") or 0) for i in rows)
        result["prompt_tokens_per_s"] = round(read / prompt_s, 1)
    cpu = [float(i["cpu_s"]) for i in rows if i.get("cpu_s") is not None]
    if cpu:
        result["cpu_s_mean"] = round(statistics.fmean(cpu), 2)
        result["cpu_s_p50"] = round(_percentile(cpu, 0.5), 2)
    return result
