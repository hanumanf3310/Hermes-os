"""Regression sentinels for restored /model picker catalog parity."""

from hermes_cli.models import provider_model_ids


RECOMMENDED_OLLAMA_LAUNCH_MODELS = [
    "kimi-k2.5:cloud",
    "glm-5.1:cloud",
    "qwen3.5:cloud",
    "minimax-m2.7:cloud",
]


def test_ollama_launch_provider_catalog_preserves_recommended_cloud_models():
    """Ollama Launch picker must retain the four documented cloud models."""
    assert provider_model_ids("ollama-launch")[:4] == RECOMMENDED_OLLAMA_LAUNCH_MODELS


def test_ollama_launch_user_config_merges_without_erasing_recommended_models(monkeypatch):
    """A config subset/extra must not hide Ollama Launch recommended models."""
    from hermes_cli.model_switch import list_authenticated_providers

    monkeypatch.setattr("agent.models_dev.fetch_models_dev", lambda: {})
    monkeypatch.setattr("agent.models_dev.PROVIDER_TO_MODELS_DEV", {})

    providers = list_authenticated_providers(
        current_provider="ollama-launch",
        user_providers={
            "ollama-launch": {
                "name": "Ollama",
                "api": "http://127.0.0.1:11434/v1",
                "default_model": "kimi-k2.6:cloud",
                "models": ["kimi-k2.6:cloud", "gemma4:26b"],
            }
        },
        max_models=10,
    )

    ollama = next(p for p in providers if p["slug"] == "ollama-launch")
    for model in RECOMMENDED_OLLAMA_LAUNCH_MODELS:
        assert model in ollama["models"]
    assert "kimi-k2.6:cloud" in ollama["models"]
    assert "gemma4:26b" in ollama["models"]
