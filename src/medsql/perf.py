"""Mesures de coût : temps processeur consommé par la machine pendant une question.

Le LLM tourne dans un autre processus (serveur Ollama), parfois sur plusieurs cœurs : le temps
CPU de medsql seul ne dirait rien. On lit donc le temps CPU occupé de **toute la machine**
(``/proc/stat``, Linux) avant et après la question. Sur une machine dédiée, comme un runner
GitHub, c'est le coût de la question ; ailleurs, l'activité des autres programmes s'y ajoute.
Hors Linux, la mesure vaut ``None``.
"""

from __future__ import annotations

import os
from pathlib import Path

PROC_STAT = Path("/proc/stat")
# Colonnes de la ligne « cpu » : user nice system idle iowait irq softirq steal ...
_BUSY = (0, 1, 2, 5, 6, 7)


def cpu_busy_seconds(stat: Path = PROC_STAT) -> float | None:
    """Temps CPU occupé cumulé de la machine depuis le démarrage, en secondes (tous cœurs)."""
    try:
        first = stat.read_text().splitlines()[0].split()
        ticks = os.sysconf("SC_CLK_TCK")
    except (OSError, IndexError, ValueError, AttributeError):
        return None
    if first[0] != "cpu":
        return None
    values = [int(v) for v in first[1:]]
    return sum(values[i] for i in _BUSY if i < len(values)) / ticks


class CpuMeter:
    """Temps CPU de la machine entre ``start`` et ``stop``."""

    def __init__(self, stat: Path = PROC_STAT) -> None:
        self.stat = stat
        self._start: float | None = None

    def start(self) -> None:
        self._start = cpu_busy_seconds(self.stat)

    def stop(self) -> float | None:
        end = cpu_busy_seconds(self.stat)
        if self._start is None or end is None:
            return None
        return round(max(0.0, end - self._start), 3)
