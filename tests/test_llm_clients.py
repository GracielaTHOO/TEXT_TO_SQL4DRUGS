from __future__ import annotations

import json

import httpx

from medsql.config import Settings
from medsql.llm import OllamaClient, OpenAICompatClient, make_client
from medsql.llm.base import Message


def test_ollama_client_parses_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url.path == "/api/chat"
        assert body["stream"] is False
        assert body["options"]["temperature"] == 0.0
        return httpx.Response(
            200, json={"message": {"content": "SELECT 1"}, "prompt_eval_count": 50, "eval_count": 5}
        )

    client = OllamaClient("m", transport=httpx.MockTransport(handler))
    completion = client.complete([Message("user", "q")])
    assert completion.text == "SELECT 1"
    assert completion.prompt_tokens == 50
    assert completion.completion_tokens == 5


def test_openai_client_parses_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer k"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "SELECT 2"}}],
                "usage": {"prompt_tokens": 40, "completion_tokens": 4},
            },
        )

    client = OpenAICompatClient("m", api_key="k", transport=httpx.MockTransport(handler))
    completion = client.complete([Message("user", "q")])
    assert completion.text == "SELECT 2"
    assert completion.completion_tokens == 4


def test_make_client_dispatch() -> None:
    assert isinstance(make_client(Settings(backend="ollama")), OllamaClient)
    assert isinstance(make_client(Settings(backend="vllm")), OpenAICompatClient)
