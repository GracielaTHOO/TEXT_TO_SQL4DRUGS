"""Clients LLM interchangeables (Ollama, API compatible OpenAI : vLLM, llama.cpp…)."""

from __future__ import annotations

from medsql.config import Settings
from medsql.llm.base import Completion, LLMClient
from medsql.llm.ollama import OllamaClient
from medsql.llm.openai_compat import OpenAICompatClient

__all__ = ["Completion", "LLMClient", "OllamaClient", "OpenAICompatClient", "make_client"]


def make_client(settings: Settings) -> LLMClient:
    """Instancie le client correspondant à ``settings.backend``."""
    if settings.backend == "ollama":
        return OllamaClient(
            settings.model, settings.base_url, settings.timeout_s, max_tokens=settings.max_tokens
        )
    if settings.backend in {"openai", "vllm", "llamacpp"}:
        return OpenAICompatClient(
            settings.model,
            settings.base_url,
            settings.timeout_s,
            api_key=settings.api_key,
            max_tokens=settings.max_tokens,
        )
    raise ValueError(f"Backend inconnu : {settings.backend!r} (ollama, openai, vllm, llamacpp)")
