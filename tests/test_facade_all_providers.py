"""SupafoneLabs end-to-end for EVERY provider: native caller event in, belief +
directive out, compiled to that provider's native injection (offline FakeLLM)."""
from __future__ import annotations

import pytest

from supafone_labs import SupafoneLabs, supercharge
from supafone_labs.llm import FakeLLMProvider
from supafone_labs.oracle.session import OracleSession

from tests.test_adapters import CASES

INJECTABLE = sorted(n for n, c in CASES.items() if c.inject_kind is not None)
TAP_ONLY = sorted(n for n, c in CASES.items() if c.inject_kind is None)


def _brain(provider: str) -> SupafoneLabs:
    return SupafoneLabs(
        provider=provider,
        oracle=OracleSession(provider=FakeLLMProvider()),
        mode="return",
    )


@pytest.mark.parametrize("name", INJECTABLE)
async def test_end_to_end_directive_compiles_natively(name):
    case = CASES[name]
    brain = _brain(name)
    result = await brain.observe(case.caller)
    assert result.belief is not None and result.belief.case_type == "auto_accident"
    assert result.directive is not None and result.directive.composed_text()
    assert result.decision is not None
    assert result.actions, f"{name}: no native action compiled"
    assert result.actions[0].provider == case.adapter.provider_name
    assert result.actions[0].kind == case.inject_kind


@pytest.mark.parametrize("name", TAP_ONLY)
async def test_tap_only_providers_observe_but_never_inject(name):
    case = CASES[name]
    brain = _brain(name)
    result = await brain.observe(case.caller)
    # The oracle still forms a belief and a directive from the tap...
    assert result.belief is not None
    assert result.directive is not None
    # ...but a raw speech engine has nothing to inject into.
    assert result.actions == []
    assert result.injected is False


async def test_unknown_provider_falls_back_to_generic():
    brain = _brain("some_future_platform")
    result = await brain.observe(
        {"type": "message", "role": "user", "text": "I was rear-ended yesterday.", "session_id": "x1"}
    )
    assert result.events, "generic fallback should still parse conventional payloads"
    assert result.actions and result.actions[0].provider == "generic"


@pytest.mark.parametrize(
    ("agent_cls_name", "expected"),
    [
        ("UltravoxAgent", "ultravox"),
        ("VapiAssistant", "vapi"),
        ("RetellPhoneAgent", "retell"),
        ("ElevenLabsConvAI", "elevenlabs"),
        ("DeepgramVoiceAgent", "deepgram"),
        ("PipecatPipeline", "pipecat"),
        ("LivekitSession", "livekit"),
        ("GrokRealtimeBot", "grok"),
    ],
)
async def test_provider_autodetected_from_agent(agent_cls_name, expected):
    agent = type(agent_cls_name, (), {})()
    brain = supercharge(agent, mode="return")
    assert brain.default_provider == expected


async def test_provider_autodetected_from_attribute():
    class Agent:
        provider = "deepgram"

    brain = supercharge(Agent(), mode="return")
    assert brain.default_provider == "deepgram"


@pytest.mark.parametrize("name", INJECTABLE)
async def test_apply_mode_injects_for_every_injectable_provider(name):
    case = CASES[name]
    got: list = []

    class Agent:
        provider_name = name

        def inject(self, actions):
            got.extend(actions)

    brain = supercharge(
        Agent(),
        scenario="legal_intake",
        oracle=OracleSession(provider=FakeLLMProvider()),
    )
    result = await brain.observe(case.caller)
    assert result.injected is True
    assert got and got[0].kind == case.inject_kind
