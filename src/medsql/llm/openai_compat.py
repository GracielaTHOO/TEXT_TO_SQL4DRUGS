"""Client pour toute API compatible OpenAI ``/v1/chat/completions``.

Couvre vLLM (``vllm serve``), llama.cpp (``llama-server``), LM Studio, etc.
"""

from __future__ import annotations

import time
from dataclasses import asdict

import httpx

from medsql.llm.base import Completion, Message


class OpenAICompatClient:
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:8000",
        timeout_s: float = 180,
        *,
        api_key: str = "",
        max_tokens: int = 512,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout_s, headers=headers, transport=transport
        )

    def complete(self, messages: list[Message], *, temperature: float = 0.0) -> Completion:
        payload = {
            "model": self.model,
            "messages": [asdict(m) for m in messages],
            "temperature": temperature,
            "max_tokens": self.max_tokens,
            "seed": 42,
        }
        start = time.perf_counter()
        response = self._client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        usage = data.get("usage") or {}
        return Completion(
            text=data["choices"][0]["message"]["content"],
            latency_s=time.perf_counter() - start,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )
