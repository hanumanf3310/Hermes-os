"""Shared auxiliary client router for side tasks - Boss Edition v2.0

Provides a single resolution chain for auxiliary tasks using ONLY:
- Primary: kimi-k2.5:cloud via Ollama
- Fallback: OpenCode models (big-pickle → minimax-m2.5-free → nemotron-3-super-free)

DEPRECATED providers (disabled per Boss policy):
- OpenRouter (was: OPENROUTER_API_KEY)
- Nous Portal (was: ~/.hermes/auth.json)
- Codex OAuth (was: chatgpt.com)
- Native Anthropic (was: Claude models)
- Direct API-key providers (was: Gemini, GLM, etc.)

Resolution order for text/vision tasks (auto mode):
  1. Ollama kimi-k2.5:cloud (primary)
  2. OpenCode big-pickle (fallback 1)
  3. OpenCode minimax-m2.5-free (fallback 2)
  4. OpenCode nemotron-3-super-free (fallback 3)
  5. None (fail gracefully)

Per-task overrides configured in config.yaml under ``auxiliary:`` section
use the same provider chain above.

Boss Policy: NO GPT, NO Claude, NO Gemini in auxiliary chain.
"""

import json
import logging
import os
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from agent.credential_pool import load_pool
from hermes_cli.config import get_hermes_home

logger = logging.getLogger(__name__)

# Module-level flag: only warn once per process
_stale_base_url_warned = False

# ═══════════════════════════════════════════════════════════════════════════════
# BOSS POLICY: Approved providers and models only
# ═══════════════════════════════════════════════════════════════════════════════

# Provider aliases - only Ollama and OpenCode permitted
_PROVIDER_ALIASES = {
    "ollama": "ollama",
    "ollama-launch": "ollama",
    "local": "ollama",
    "opencode": "opencode",
    "open-code": "opencode",
}

# BOSS APPROVED: Auxiliary model fallback chain
# Order: Primary → Fallback 1 → Fallback 2 → Fallback 3
_AUX_MODEL_FALLBACK_CHAIN: List[Tuple[str, str, str]] = [
    # (provider, model, base_url)
    ("ollama", "kimi-k2.5:cloud", "http://127.0.0.1:11434/v1"),
    ("opencode", "gpt-5.4-mini", "https://api.opencode.ai/v1"),
    ("opencode", "opencode/minimax-m2.5-free", "https://api.opencode.ai/v1"),
    ("opencode", "opencode/nemotron-3-super-free", "https://api.opencode.ai/v1"),
]

# Default for Ollama (primary)
_OLLAMA_MODEL = "kimi-k2.5:cloud"
_OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"

# Default for OpenCode fallbacks
_OPENCODE_BASE_URL = "https://api.opencode.ai/v1"
_OPENCODE_API_KEY_ENV = "OPENCODE_API_KEY"

# DEPRECATED: These providers are DISABLED per Boss policy
_DEPRECATED_PROVIDERS = frozenset({
    "openrouter", "nous", "anthropic", "openai-codex", "codex",
    "gemini", "google", "google-gemini", "zai", "glm", "minimax", "minimax-cn",
    "deepseek", "alibaba", "xiaomi", "kilocode"
})

# DEPRECATED: Model references removed
_DEPRECATED_MODELS = frozenset({
    "gpt-5.2-codex", "gpt-4o-mini", "gpt-4o", "claude-haiku", "claude-sonnet",
    "gemini-3-flash", "gemini-3-pro", "glm-4", "glm-5"
})


def _normalize_aux_provider(provider: Optional[str]) -> str:
    """Normalize provider name to approved list only."""
    normalized = (provider or "auto").strip().lower()
    
    # Check for deprecated providers - warn and redirect to approved
    if normalized in _DEPRECATED_PROVIDERS:
        logger.warning(
            "Provider '%s' is DEPRECATED per Boss policy. "
            "Falling back to approved chain (ollama -> opencode).",
            normalized
        )
        return "auto"  # Will use approved fallback chain
    
    if normalized.startswith("custom:"):
        suffix = normalized.split(":", 1)[1].strip()
        if not suffix:
            return "ollama"  # Default to primary
        normalized = suffix
    
    if normalized == "main":
        # Resolve to ollama per Boss policy
        return "ollama"
    
    return _PROVIDER_ALIASES.get(normalized, normalized if normalized in _PROVIDER_ALIASES else "auto")


def _is_deprecated_provider(provider: str) -> bool:
    """Check if provider is deprecated per Boss policy."""
    return provider.lower() in _DEPRECATED_PROVIDERS


# ═══════════════════════════════════════════════════════════════════════════════
# Ollama / Kimi Configuration
# ═══════════════════════════════════════════════════════════════════════════════

def _get_ollama_client() -> Optional[Tuple[OpenAI, str]]:
    """Get Ollama client for kimi-k2.5:cloud (Primary)."""
    try:
        # Check if Ollama is reachable
        import urllib.request
        req = urllib.request.Request(
            f"{_OLLAMA_BASE_URL}/models",
            method="GET",
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    logger.debug("Ollama server is reachable at %s", _OLLAMA_BASE_URL)
        except Exception as e:
            logger.debug("Ollama health check warning (will retry): %s", e)
            # Don't fail here - let the actual API call determine success
        
        # Create client with Ollama base URL
        client = OpenAI(
            base_url=_OLLAMA_BASE_URL,
            api_key="ollama",  # Ollama doesn't require real API key
            timeout=120,
        )
        logger.debug("Auxiliary client: Ollama (kimi-k2.5:cloud)")
        return client, _OLLAMA_MODEL
        
    except Exception as e:
        logger.debug("Ollama client creation failed: %s", e)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# OpenCode Fallback Configuration  
# ═══════════════════════════════════════════════════════════════════════════════

def _get_opencode_client(model: str = "gpt-5.4-mini") -> Optional[Tuple[OpenAI, str]]:
    """Get OpenCode client for fallback models."""
    api_key = os.getenv(_OPENCODE_API_KEY_ENV)
    
    # Try to get from credential pool if env not set
    if not api_key:
        try:
            pool_present, entry = _select_pool_entry("opencode")
            if pool_present and entry:
                api_key = _pool_runtime_api_key(entry)
        except Exception:
            pass
    
    if not api_key:
        logger.debug("OpenCode API key not found in env or credential pool")
        return None
    
    try:
        client = OpenAI(
            base_url=_OPENCODE_BASE_URL,
            api_key=api_key,
            timeout=120,
        )
        logger.debug("Auxiliary client: OpenCode (%s)", model)
        return client, model
        
    except Exception as e:
        logger.debug("OpenCode client creation failed: %s", e)
        return None


def _try_opencode_with_fallback() -> Optional[Tuple[OpenAI, str]]:
    """Try OpenCode models in fallback order."""
    models = [
        "gpt-5.4-mini",
        "opencode/minimax-m2.5-free", 
        "opencode/nemotron-3-super-free"
    ]
    
    for model in models:
        result = _get_opencode_client(model)
        if result:
            logger.info("Auxiliary auto-detect: using OpenCode fallback (%s)", model)
            return result
    
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Credential Pool Helpers (retained for OpenCode auth)
# ═══════════════════════════════════════════════════════════════════════════════

def _select_pool_entry(provider: str) -> Tuple[bool, Optional[Any]]:
    """Return (pool_exists_for_provider, selected_entry)."""
    # Skip deprecated providers
    if _is_deprecated_provider(provider):
        logger.debug("Skipping credential pool for deprecated provider: %s", provider)
        return False, None
    
    try:
        pool = load_pool(provider)
    except Exception as exc:
        logger.debug("Auxiliary client: could not load pool for %s: %s", provider, exc)
        return False, None
    if not pool or not pool.has_credentials():
        return False, None
    try:
        return True, pool.select()
    except Exception as exc:
        logger.debug("Auxiliary client: could not select pool entry for %s: %s", provider, exc)
        return True, None


def _pool_runtime_api_key(entry: Any) -> str:
    if entry is None:
        return ""
    key = getattr(entry, "runtime_api_key", None) or getattr(entry, "access_token", "")
    return str(key or "").strip()


def _pool_runtime_base_url(entry: Any, fallback: str = "") -> str:
    if entry is None:
        return str(fallback or "").strip().rstrip("/")
    url = (
        getattr(entry, "runtime_base_url", None)
        or getattr(entry, "inference_base_url", None)
        or getattr(entry, "base_url", None)
        or fallback
    )
    return str(url or "").strip().rstrip("/")


# ═══════════════════════════════════════════════════════════════════════════════
# DEPRECATED: Legacy provider functions (kept for reference, return None)
# ═══════════════════════════════════════════════════════════════════════════════

def _try_openrouter() -> Tuple[Optional[OpenAI], Optional[str]]:
    """DEPRECATED: OpenRouter disabled per Boss policy."""
    logger.debug("OpenRouter is DISABLED per Boss policy - skipping")
    return None, None


def _try_nous() -> Tuple[Optional[OpenAI], Optional[str]]:
    """DEPRECATED: Nous Portal disabled per Boss policy."""
    logger.debug("Nous Portal is DISABLED per Boss policy - skipping")
    return None, None


def _try_codex() -> Tuple[Optional[Any], Optional[str]]:
    """DEPRECATED: Codex OAuth disabled per Boss policy."""
    logger.debug("Codex OAuth is DISABLED per Boss policy - skipping")
    return None, None


def _try_anthropic() -> Tuple[Optional[Any], Optional[str]]:
    """DEPRECATED: Native Anthropic disabled per Boss policy."""
    logger.debug("Native Anthropic is DISABLED per Boss policy - skipping")
    return None, None


def _try_api_key_providers() -> Tuple[Optional[OpenAI], Optional[str]]:
    """DEPRECATED: Direct API-key providers disabled per Boss policy."""
    logger.debug("Direct API-key providers (Gemini, GLM, etc.) DISABLED per Boss policy - skipping")
    return None, None


# ═══════════════════════════════════════════════════════════════════════════════
# Main Resolution Chain
# ═══════════════════════════════════════════════════════════════════════════════

def _resolve_auto(main_runtime: Optional[Dict[str, Any]] = None) -> Tuple[Optional[OpenAI], Optional[str]]:
    """Boss-approved auto-detection chain.
    
    Priority:
      1. Ollama kimi-k2.5:cloud (Primary)
      2. OpenCode big-pickle (Fallback 1)
      3. OpenCode minimax-m2.5-free (Fallback 2)
      4. OpenCode nemotron-3-super-free (Fallback 3)
      5. None (fail gracefully with warning)
    """
    global _stale_base_url_warned
    
    # Step 1: Try Ollama (kimi-k2.5:cloud) - PRIMARY
    logger.debug("Auxiliary auto-detect: trying Ollama (kimi-k2.5:cloud)...")
    ollama_result = _get_ollama_client()
    if ollama_result:
        logger.info("Auxiliary auto-detect: using Ollama (kimi-k2.5:cloud)")
        return ollama_result
    
    logger.debug("Ollama unavailable, trying OpenCode fallbacks...")
    
    # Step 2: Try OpenCode fallbacks
    opencode_result = _try_opencode_with_fallback()
    if opencode_result:
        return opencode_result
    
    # All approved providers exhausted
    logger.warning(
        "Auxiliary auto-detect: ALL approved providers unavailable "
        "(Ollama: %s, OpenCode: %s). "
        "Context compression, summarization, and vision will not work. "
        "Please ensure Ollama is running at %s or OpenCode API key is set.",
        "failed to connect", "no API key", _OLLAMA_BASE_URL
    )
    return None, None


def resolve_provider_client(
    provider: str,
    model: str = None,
    async_mode: bool = False,
    explicit_base_url: str = None,
    explicit_api_key: str = None,
    api_mode: str = None,
    main_runtime: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Any], Optional[str]]:
    """Central router - Boss approved providers only.
    
    Approved providers:
    - "ollama" or "auto" -> uses Ollama kimi-k2.5:cloud
    - "opencode" -> uses OpenCode with fallback chain
    
    DEPRECATED (return None with warning):
    - "openrouter", "nous", "openai-codex", "anthropic"
    - "gemini", "google", "zai", "minimax", "deepseek", etc.
    """
    # Normalize and check for deprecated
    provider = _normalize_aux_provider(provider)
    
    if provider in _DEPRECATED_PROVIDERS:
        logger.warning(
            "Provider '%s' is DEPRECATED per Boss policy. "
            "Use 'ollama' (primary) or 'opencode' (fallback).",
            provider
        )
        return None, None
    
    # Auto-detect uses approved chain
    if provider == "auto":
        client, resolved_model = _resolve_auto(main_runtime=main_runtime)
        if client is None:
            return None, None
        final_model = model or resolved_model
        return (_to_async_client(client, final_model) if async_mode 
                else (client, final_model))
    
    # Ollama (Boss primary)
    if provider == "ollama":
        client, default = _get_ollama_client()
        if client is None:
            logger.warning("resolve_provider_client: Ollama unavailable at %s", _OLLAMA_BASE_URL)
            return None, None
        final_model = model or default
        return (_to_async_client(client, final_model) if async_mode 
                else (client, final_model))
    
    # OpenCode (Boss fallback)
    if provider == "opencode":
        final_model = model or "gpt-5.4-mini"
        client, _ = _get_opencode_client(final_model)
        if client is None:
            # Try fallback models
            for fallback_model in ["opencode/minimax-m2.5-free", "opencode/nemotron-3-super-free"]:
                client, _ = _get_opencode_client(fallback_model)
                if client:
                    final_model = fallback_model
                    break
        if client is None:
            logger.warning("resolve_provider_client: OpenCode unavailable (no API key)")
            return None, None
        return (_to_async_client(client, final_model) if async_mode 
                else (client, final_model))
    
    # Unknown provider
    logger.warning("resolve_provider_client: unknown provider '%s'", provider)
    return None, None


def _to_async_client(sync_client, model: str):
    """Convert sync client to async."""
    from openai import AsyncOpenAI
    
    async_kwargs = {
        "api_key": sync_client.api_key,
        "base_url": str(sync_client.base_url),
    }
    return AsyncOpenAI(**async_kwargs), model


# ═══════════════════════════════════════════════════════════════════════════════
# Public API - Retained for compatibility
# ═══════════════════════════════════════════════════════════════════════════════

def get_auxiliary_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: Optional[int] = None,
    vision: bool = False,
    main_runtime: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Any], Optional[str]]:
    """Get auxiliary client - Boss approved chain only."""
    # Force auto mode to use approved chain
    if provider in _DEPRECATED_PROVIDERS or provider is None:
        if provider:
            logger.warning("Provider '%s' deprecated, using approved chain", provider)
        provider = "auto"
    
    return resolve_provider_client(
        provider=provider,
        model=model,
        async_mode=False,
        explicit_base_url=base_url,
        explicit_api_key=api_key,
        main_runtime=main_runtime,
    )


def get_async_auxiliary_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: Optional[int] = None,
    vision: bool = False,
    main_runtime: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Any], Optional[str]]:
    """Get async auxiliary client - Boss approved chain only."""
    if provider in _DEPRECATED_PROVIDERS or provider is None:
        if provider:
            logger.warning("Provider '%s' deprecated, using approved chain", provider)
        provider = "auto"
    
    return resolve_provider_client(
        provider=provider,
        model=model,
        async_mode=True,
        explicit_base_url=base_url,
        explicit_api_key=api_key,
        main_runtime=main_runtime,
    )


# Legacy alias for compatibility
call_llm = get_auxiliary_client


# ═══════════════════════════════════════════════════════════════════════════════
# Backwards compatibility stubs (raise RuntimeError if called)
# ═══════════════════════════════════════════════════════════════════════════════

class CodexAuxiliaryClient:
    """DEPRECATED: Codex OAuth disabled per Boss policy."""
    def __init__(self, *args, **kwargs):
        raise RuntimeError("CodexAuxiliaryClient is DEPRECATED per Boss policy. Use Ollama or OpenCode.")


class AnthropicAuxiliaryClient:
    """DEPRECATED: Native Anthropic disabled per Boss policy."""
    def __init__(self, *args, **kwargs):
        raise RuntimeError("AnthropicAuxiliaryClient is DEPRECATED per Boss policy. Use Ollama or OpenCode.")


# Module exports
__all__ = [
    "get_auxiliary_client",
    "get_async_auxiliary_client",
    "call_llm",
    "resolve_provider_client",
    "_DEPRECATED_PROVIDERS",
]
