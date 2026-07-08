"""Provider resolution: explicit by name, or auto by tier and available keys.

Auto order:
1. ``SUPAFONE_LABS_API_KEY`` set  -> HostedLLMProvider (pro tier, Supafone Labs' keys)
2. ``ANTHROPIC_API_KEY`` set   -> AnthropicProvider (free tier, your key)
3. ``OPENAI_API_KEY`` set      -> OpenAIProvider (free tier, your key)
4. no keys                     -> FakeLLMProvider (offline, deterministic)
"""
from __future__ import annotations

import os
from typing import Any

from supafone_labs.llm.base import AnthropicProvider, FakeLLMProvider, LLMProvider
from supafone_labs.tiers import license_key


def get_provider(name: str | None = None, **kwargs: Any) -> LLMProvider:
    """Return a provider by name ('fake' | 'anthropic' | 'openai' | 'hosted'), or auto-resolve."""
    if name == "fake":
        return FakeLLMProvider()
    if name == "anthropic":
        return AnthropicProvider(**kwargs)
    if name == "openai":
        from supafone_labs.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(**kwargs)
    if name == "xai":
        from supafone_labs.llm.openai_provider import OpenAIProvider

        kwargs.setdefault("base_url", "https://api.x.ai/v1")
        kwargs.setdefault("api_key", os.getenv("XAI_API_KEY"))
        kwargs.setdefault("model", "grok-4-fast")
        return OpenAIProvider(**kwargs)
    if name == "hosted":
        from supafone_labs.llm.hosted_provider import HostedLLMProvider

        return HostedLLMProvider(**kwargs)
    # auto: paid hosted first, then BYO keys, then the offline fake
    if license_key():
        from supafone_labs.llm.hosted_provider import HostedLLMProvider

        return HostedLLMProvider(**kwargs)
    if os.getenv("ANTHROPIC_API_KEY"):
        return AnthropicProvider(**kwargs)
    if os.getenv("OPENAI_API_KEY"):
        from supafone_labs.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(**kwargs)
    return FakeLLMProvider()


def get_default_provider() -> LLMProvider:
    """Auto-resolved default provider."""
    return get_provider()


# MANIFEST-compatible alias.
build_llm_provider = get_provider
