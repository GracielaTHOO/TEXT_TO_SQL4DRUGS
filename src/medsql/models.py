"""Catalogue des modèles comparés : famille, éditeur, taille, spécialité, licence.

Sert à présenter la comparaison multi-familles (S9) : à taille voisine, un modèle de code
fait-il mieux qu'un généraliste, et un modèle entraîné pour le SQL mieux qu'un modèle de code ?
Les tailles sont celles annoncées par les éditeurs, arrondies ; les modèles tournent en
quantification 4 bits (étiquettes Ollama par défaut).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    family: str
    publisher: str
    params_b: float  # milliards de paramètres
    specialty: str  # « généraliste », « code » ou « SQL »
    licence: str


MODELS: dict[str, ModelInfo] = {
    "qwen2.5-coder:1.5b": ModelInfo("Qwen2.5-Coder", "Alibaba", 1.5, "code", "Apache 2.0"),
    "qwen2.5-coder:3b": ModelInfo("Qwen2.5-Coder", "Alibaba", 3.1, "code", "Qwen Research"),
    "qwen2.5-coder:7b": ModelInfo("Qwen2.5-Coder", "Alibaba", 7.6, "code", "Apache 2.0"),
    "llama3.1:8b": ModelInfo("Llama 3.1", "Meta", 8.0, "généraliste", "Llama 3.1 Community"),
    "mistral:7b": ModelInfo("Mistral", "Mistral AI", 7.2, "généraliste", "Apache 2.0"),
    "gemma2:9b": ModelInfo("Gemma 2", "Google", 9.2, "généraliste", "Gemma Terms of Use"),
    "sqlcoder:7b": ModelInfo("SQLCoder", "Defog", 7.0, "SQL", "CC BY-SA 4.0"),
}


def model_info(model: str) -> ModelInfo | None:
    """Fiche d'un modèle (étiquette Ollama), ``None`` s'il n'est pas catalogué."""
    return MODELS.get(model.strip().lower())
