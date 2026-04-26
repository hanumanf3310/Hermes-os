"""Regression sentinels for restored /model picker catalog parity.

These tests encode Boss's pre-update expectations for OpenAI Codex and
Ollama Launch so future upstream updates cannot silently revert the custom
picker behavior.
"""

from hermes_cli.models import provider_model_ids, validate_requested_model


RECOMMENDED_OLLAMA_LAUNCH_MODELS = [
    "kimi-k2.5:cloud",
    "glm-5.1:cloud",
    "qwen3.5:cloud",
    "minimax-m2.7:cloud",
]


def test_provider_model_ids_passes_runtime_api_key_to_codex_catalog(monkeypatch):
    """Codex picker/catalog lookup must use the runtime OAuth token."""
    captured = {}

    def fake_get_codex_model_ids(*, access_token=None):
        captured["access_token"] = access_token
        return ["gpt-5.3-codex-spark"]

    monkeypatch.setattr(
        "hermes_cli.codex_models.get_codex_model_ids",
        fake_get_codex_model_ids,
    )

    assert provider_model_ids("openai-codex", api_key="runtime-codex-token") == [
        "gpt-5.3-codex-spark"
    ]
    assert captured["access_token"] == "runtime-codex-token"


def test_codex_validation_uses_same_runtime_catalog_as_picker(monkeypatch):
    """A picker-visible live Codex model must validate with the same token-backed catalog."""
    captured = {}

    def fake_provider_model_ids(provider, *, force_refresh=False, api_key=None):
        captured["provider"] = provider
        captured["api_key"] = api_key
        return ["gpt-5.3-codex-spark"]

    monkeypatch.setattr("hermes_cli.models.provider_model_ids", fake_provider_model_ids)

    result = validate_requested_model(
        "gpt-5.3-codex-spark",
        "openai-codex",
        api_key="runtime-codex-token",
    )

    assert result["accepted"] is True
    assert result["recognized"] is True
    assert captured == {
        "provider": "openai-codex",
        "api_key": "runtime-codex-token",
    }


def test_openai_codex_picker_uses_runtime_catalog_not_static_fallback(tmp_path, monkeypatch):
    """Telegram /model picker must render Codex models from the runtime catalog."""
    import json

    from hermes_cli.model_switch import list_authenticated_providers

    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "no-codex"))
    (hermes_home / "auth.json").write_text(json.dumps({
        "version": 2,
        "providers": {
            "openai-codex": {
                "tokens": {
                    "access_token": "runtime-codex-token",
                    "refresh_token": "refresh-token",
                }
            }
        },
    }))
    monkeypatch.setattr("agent.models_dev.fetch_models_dev", lambda: {})
    monkeypatch.setattr("agent.models_dev.PROVIDER_TO_MODELS_DEV", {})
    monkeypatch.setattr(
        "hermes_cli.models.provider_model_ids",
        lambda provider, **kwargs: ["gpt-5.3-codex-spark", "gpt-5.3-codex"]
        if provider == "openai-codex"
        else [],
    )

    providers = list_authenticated_providers(current_provider="openai-codex", max_models=10)

    codex = next(p for p in providers if p["slug"] == "openai-codex")
    assert codex["models"] == ["gpt-5.3-codex-spark", "gpt-5.3-codex"]
    assert "gpt-5.2-codex" not in codex["models"]


def test_ollama_launch_provider_catalog_preserves_recommended_cloud_models():
    """Ollama Launch picker must retain the four documented cloud models."""
    from hermes_cli.models import _PROVIDER_MODELS

    assert _PROVIDER_MODELS["ollama-launch"][:4] == RECOMMENDED_OLLAMA_LAUNCH_MODELS


def test_ollama_launch_validation_accepts_recommended_cloud_models_when_listing_omits_them(monkeypatch):
    """Ollama Launch cloud models must be selectable even if /models is incomplete."""
    monkeypatch.setattr("hermes_cli.models.fetch_api_models", lambda *a, **k: ["gemma4:26b"])

    for model in RECOMMENDED_OLLAMA_LAUNCH_MODELS:
        result = validate_requested_model(
            model,
            "ollama-launch",
            api_key="ollama",
            base_url="http://127.0.0.1:11434/v1",
        )
        assert result["accepted"] is True
        assert result["persist"] is True


def test_ollama_launch_user_config_merges_without_erasing_recommended_models(monkeypatch):
    """A config subset/extra must not hide Ollama Launch recommended models."""
    from hermes_cli.model_switch import list_authenticated_providers

    monkeypatch.setattr("agent.models_dev.fetch_models_dev", lambda: {})
    monkeypatch.setattr("agent.models_dev.PROVIDER_TO_MODELS_DEV", {})
    monkeypatch.setenv("OLLAMA_API_KEY", "test-ollama-key")

    providers = list_authenticated_providers(
        current_provider="ollama-launch",
        user_providers={
            "ollama-launch": {
                "name": "Ollama Launch",
                "base_url": "https://ollama.com/v1",
                "model": "qwen3.5:cloud",
                "models": {"custom-extra:cloud": {}},
            }
        },
        max_models=10,
    )

    ollama = next(p for p in providers if p["slug"] == "ollama-launch")
    for model in RECOMMENDED_OLLAMA_LAUNCH_MODELS:
        assert model in ollama["models"]
    assert "custom-extra:cloud" in ollama["models"]
