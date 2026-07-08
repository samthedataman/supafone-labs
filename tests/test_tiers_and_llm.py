"""Tier resolution + LLM registry: free = your keys, paid = Supafone Labs' keys."""
from __future__ import annotations

import pytest

from supafone_labs.llm import (
    AnthropicProvider,
    FakeLLMProvider,
    HostedLLMProvider,
    OpenAIProvider,
    build_llm_provider,
    get_provider,
)
from supafone_labs.tiers import Tier, TierError, current_tier, has_feature, require_feature

ALL_KEYS = ("SUPAFONE_LABS_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY")


@pytest.fixture
def clean_env(monkeypatch):
    for key in ALL_KEYS:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


# --- tiers -----------------------------------------------------------------

def test_free_tier_without_license(clean_env):
    assert current_tier() is Tier.FREE
    assert has_feature("byo_oracle")
    assert has_feature("all_adapters")
    assert not has_feature("hosted_oracle")
    with pytest.raises(TierError):
        require_feature("hosted_oracle")


def test_pro_tier_with_license(clean_env):
    clean_env.setenv("SUPAFONE_LABS_API_KEY", "sl_live_123")
    assert current_tier() is Tier.PRO
    assert has_feature("hosted_oracle")
    assert has_feature("hosted_tts")
    require_feature("hosted_tts")  # must not raise


def test_free_tier_never_loses_features(clean_env):
    from supafone_labs.tiers import FEATURES

    assert FEATURES[Tier.FREE] <= FEATURES[Tier.PRO]


# --- LLM registry ----------------------------------------------------------

def test_auto_resolves_fake_with_no_keys(clean_env):
    assert isinstance(get_provider(), FakeLLMProvider)


def test_auto_prefers_hosted_when_licensed(clean_env):
    clean_env.setenv("SUPAFONE_LABS_API_KEY", "sl_live_123")
    clean_env.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    assert isinstance(get_provider(), HostedLLMProvider)


def test_auto_uses_anthropic_key_on_free_tier(clean_env):
    clean_env.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    assert isinstance(get_provider(), AnthropicProvider)


def test_auto_falls_back_to_openai_key(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "sk-x")
    assert isinstance(get_provider(), OpenAIProvider)


def test_explicit_names_and_manifest_alias(clean_env):
    assert isinstance(get_provider("fake"), FakeLLMProvider)
    assert isinstance(get_provider("anthropic"), AnthropicProvider)
    assert isinstance(get_provider("openai"), OpenAIProvider)
    assert isinstance(get_provider("hosted"), HostedLLMProvider)
    assert build_llm_provider is get_provider or isinstance(build_llm_provider("fake"), FakeLLMProvider)


# --- hosted provider -------------------------------------------------------

class _MockResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _MockClient:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[dict] = []

    async def post(self, url, headers=None, json=None, params=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return _MockResponse(self.payload)

    async def aclose(self) -> None:
        return None


async def test_hosted_provider_round_trip(clean_env):
    client = _MockClient({"text": '{"confidence": 0.9}'})
    provider = HostedLLMProvider(api_key="sl_live_123", client=client)
    out = await provider.complete([{"role": "user", "content": "hi"}], model="oracle-1")
    assert out == '{"confidence": 0.9}'
    call = client.calls[0]
    assert call["url"].endswith("/oracle/complete")
    assert call["headers"]["Authorization"] == "Bearer sl_live_123"
    assert call["json"]["model"] == "oracle-1"


async def test_hosted_provider_requires_license(clean_env):
    provider = HostedLLMProvider(api_key="", client=_MockClient({}))
    with pytest.raises(TierError):
        await provider.complete([{"role": "user", "content": "hi"}])


async def test_hosted_provider_honors_api_base(clean_env):
    clean_env.setenv("SUPAFONE_LABS_API_BASE", "https://sm.example.com/api/")
    client = _MockClient({"text": "ok"})
    provider = HostedLLMProvider(api_key="sl_live_123", client=client)
    await provider.complete([{"role": "user", "content": "hi"}])
    assert client.calls[0]["url"] == "https://sm.example.com/api/oracle/complete"
