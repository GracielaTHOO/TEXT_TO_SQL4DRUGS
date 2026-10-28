from __future__ import annotations

from medsql.models import MODELS, model_info


def test_catalogue_covers_the_s9_comparison() -> None:
    for tag in ("llama3.1:8b", "mistral:7b", "gemma2:9b", "sqlcoder:7b", "qwen2.5-coder:7b"):
        assert tag in MODELS
    assert {m.specialty for m in MODELS.values()} == {"généraliste", "code", "SQL"}


def test_model_info_is_tolerant_and_optional() -> None:
    info = model_info(" Gemma2:9B ")
    assert info is not None and info.publisher == "Google"
    assert model_info("inconnu:1b") is None
