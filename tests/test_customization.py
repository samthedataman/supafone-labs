"""Pick your second-brain model, provider, and prompts — and live model discovery."""
from __future__ import annotations

import pytest

from supafone_labs import SupafoneLabs, provider_for_model
from supafone_labs.llm import AnthropicProvider, FakeLLMProvider, HostedLLMProvider, OpenAIProvider
from supafone_labs.llm.registry import get_provider
from supafone_labs.models import clear_model_cache, discover_oracle_models


@pytest.fixture
def clean_env(monkeypatch):
    for key in ("SUPAFONE_LABS_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    clear_model_cache()
    yield monkeypatch
    clear_model_cache()


# --- model -> provider inference ----------------------------------------------------

def test_provider_inferred_by_prefix_never_deprecates():
    # Future models that don't exist yet must still route correctly.
    assert provider_for_model("claude-fable-9") == "anthropic"
    assert provider_for_model("gpt-7-nano") == "openai"
    assert provider_for_model("grok-9") == "xai"
    assert provider_for_model("supafone-labs-oracle-ultra") == "hosted"


def test_second_mind_infers_llm_from_model(clean_env):
    brain = SupafoneLabs(provider="ultravox", oracle_model="claude-sonnet-4-6", mode="return")
    assert isinstance(brain.oracle.provider, AnthropicProvider)
    assert brain.oracle.config.oracle_model == "claude-sonnet-4-6"

    brain = SupafoneLabs(provider="ultravox", oracle_model="gpt-4.1-mini", mode="return")
    assert isinstance(brain.oracle.provider, OpenAIProvider)

    brain = SupafoneLabs(provider="ultravox", oracle_model="supafone-labs-oracle", mode="return")
    assert isinstance(brain.oracle.provider, HostedLLMProvider)


def test_xai_provider_is_openai_compatible(clean_env):
    provider = get_provider("xai")
    assert isinstance(provider, OpenAIProvider)
    assert provider.base_url == "https://api.x.ai/v1"


def test_explicit_llm_name_wins(clean_env):
    brain = SupafoneLabs(provider="ultravox", llm="fake", oracle_model="claude-sonnet-4-6", mode="return")
    assert isinstance(brain.oracle.provider, FakeLLMProvider)
    assert brain.oracle.config.oracle_model == "claude-sonnet-4-6"


# --- custom prompts --------------------------------------------------------------------

async def test_custom_prompts_and_instructions_reach_the_engines(clean_env):
    brain = SupafoneLabs(
        provider="ultravox",
        llm="fake",
        mode="return",
        oracle_instructions="Coach for a bilingual personal-injury intake desk.",
        directive_prompt="You are the DIRECTIVE core. Reply with JSON only.",
        belief_prompt="You are the BELIEF core. Reply with JSON only.",
    )
    assert brain.oracle.directive_gen.system_prompt.startswith("You are the DIRECTIVE core.")
    assert "bilingual personal-injury" in brain.oracle.directive_gen.system_prompt
    assert brain.oracle.belief_engine.system_prompt.startswith("You are the BELIEF core.")
    assert "bilingual personal-injury" in brain.oracle.belief_engine.system_prompt

    # The full loop still works with custom prompts (FakeLLM keys off "belief"/"directive").
    result = await brain.observe(
        {"type": "transcript", "speaker": "caller", "text": "I was rear-ended.", "final": True, "call_id": "c1"}
    )
    assert result.directive is not None and result.directive.composed_text()


# --- live model discovery ----------------------------------------------------------------

class _MockResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _MockClient:
    def __init__(self, payloads: dict[str, dict]):
        self.payloads = payloads

    async def get(self, url, headers=None):
        for fragment, payload in self.payloads.items():
            if fragment in url:
                return _MockResponse(payload)
        raise RuntimeError(f"unexpected url {url}")

    async def aclose(self):
        return None


async def test_discovery_falls_back_to_static_without_keys(clean_env):
    models = await discover_oracle_models(refresh=True, client=_MockClient({}))
    assert "claude-haiku-4-5-20251001" in models["anthropic"]
    assert models["openai"]  # static fallback present


async def test_discovery_uses_live_vendor_lists_when_keyed(clean_env):
    clean_env.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    client = _MockClient(
        {"api.anthropic.com": {"data": [{"id": "claude-fable-9"}, {"id": "claude-haiku-4-5-20251001"}]}}
    )
    models = await discover_oracle_models(refresh=True, client=client)
    assert "claude-fable-9" in models["anthropic"]  # a model newer than this package


async def test_discovery_result_is_cached(clean_env):
    clean_env.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    client = _MockClient({"api.anthropic.com": {"data": [{"id": "claude-live-1"}]}})
    first = await discover_oracle_models(refresh=True, client=client)
    second = await discover_oracle_models(client=_MockClient({}))  # would fail if not cached
    assert first == second
