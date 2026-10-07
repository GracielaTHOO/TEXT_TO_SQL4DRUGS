"""Client pour l'API native d'Ollama (https://github.com/ollama/ollama/blob/main/docs/api.md)."""

from __future__ import annotations

import time
from dataclasses import asdict

import httpx

from medsql.llm.base import Completion, Message


class OllamaClient:
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        timeout_s: float = 180,
        *,
        num_ctx: int = 8192,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model = model
        self.num_ctx = num_ctx
        self._client = httpx.Client(base_url=base_url, timeout=timeout_s, transport=transport)

    def complete(self, messages: list[Message], *, temperature: float = 0.0) -> Completion:
        payload = {
            "model": self.model,
            "messages": [asdict(m) for m in messages],
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": self.num_ctx, "seed": 42},
        }
        start = time.perf_counter()
        response = self._client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        return Completion(
            text=data["message"]["content"],
            latency_s=time.perf_counter() - start,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
        )

    def list_models(self) -> list[str]:
        response = self._client.get("/api/tags")
        response.raise_for_status()
        return [m["name"] for m in response.json().get("models", [])]
