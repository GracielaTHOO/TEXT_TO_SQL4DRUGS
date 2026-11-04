"""Interface commune aux clients LLM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(frozen=True)
class Completion:
    """Réponse d'un appel au LLM, avec les durées internes quand le serveur les donne.

    Ollama détaille son temps : chargement du modèle (``load_s``), lecture du prompt
    (``prompt_eval_s``) et génération (``eval_s``). Le temps de premier token en découle
    sans avoir à diffuser la réponse en flux. Les API compatibles OpenAI ne les donnent pas.
    """

    text: str
    latency_s: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    load_s: float | None = None
    prompt_eval_s: float | None = None
    eval_s: float | None = None

    @property
    def ttft_s(self) -> float | None:
        """Temps de premier token : chargement + lecture du prompt."""
        if self.prompt_eval_s is None:
            return None
        return (self.load_s or 0.0) + self.prompt_eval_s

    @property
    def tokens_per_s(self) -> float | None:
        """Débit de génération : tokens produits par seconde de génération pure."""
        if not self.completion_tokens:
            return None
        duration = self.eval_s if self.eval_s else self.latency_s
        return self.completion_tokens / duration if duration > 0 else None

    @property
    def prompt_tokens_per_s(self) -> float | None:
        """Débit de lecture du prompt : tokens du prompt lus par seconde."""
        if not self.prompt_tokens or not self.prompt_eval_s:
            return None
        return self.prompt_tokens / self.prompt_eval_s


class LLMClient(Protocol):
    model: str

    def complete(self, messages: list[Message], *, temperature: float = 0.0) -> Completion: ...
