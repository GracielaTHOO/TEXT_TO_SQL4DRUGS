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
    text: str
    latency_s: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    @property
    def tokens_per_s(self) -> float | None:
        if not self.completion_tokens or self.latency_s <= 0:
            return None
        return self.completion_tokens / self.latency_s


class LLMClient(Protocol):
    model: str

    def complete(self, messages: list[Message], *, temperature: float = 0.0) -> Completion: ...
