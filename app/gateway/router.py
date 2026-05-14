from __future__ import annotations

from app.gateway.providers.anthropic import AnthropicProvider
from app.gateway.providers.base import Provider
from app.gateway.providers.google import GoogleProvider
from app.gateway.providers.openai import OpenAIProvider

_openai = OpenAIProvider()
_anthropic = AnthropicProvider()
_google = GoogleProvider()

_REGISTRY: dict[str, tuple[Provider, str]] = {
    "openai": (_openai, "openai"),
    "anthropic": (_anthropic, "anthropic"),
    "google": (_google, "google"),
    "gemini": (_google, "google"),
}

_DEFAULT_PROVIDER: tuple[Provider, str] = (_openai, "openai")


def get_provider(model: str) -> tuple[Provider, str]:
    """Return (provider, canonical_name) for the given model string.

    Accepts "anthropic/claude-3-5-sonnet" or bare "gpt-4o" (defaults to OpenAI).
    """
    if "/" in model:
        prefix = model.split("/", 1)[0].lower()
        if prefix in _REGISTRY:
            return _REGISTRY[prefix]
    # bare model name heuristics
    lower = model.lower()
    if lower.startswith("claude"):
        return _REGISTRY["anthropic"]
    if lower.startswith("gemini"):
        return _REGISTRY["google"]
    return _DEFAULT_PROVIDER
