"""Nudge telemetry: full-granularity reporting, fire-and-forget, never on the call path."""
from __future__ import annotations

import asyncio

import pytest

from supafone_labs import SupafoneLabs
from supafone_labs.llm import FakeLLMProvider
from supafone_labs.oracle.session import OracleSession
from supafone_labs.telemetry import report_nudge


@pytest.fixture
def clean_env(monkeypatch):
    monkeypatch.delenv("SUPAFONE_LABS_API_KEY", raising=False)
    monkeypatch.delenv("SUPAFONE_LABS_TELEMETRY", raising=False)
    return monkeypatch


class _MockResponse:
    status_code = 200


class _MockClient:
    def __init__(self):
        self.calls: list[dict] = []

    async def post(self, url, headers=None, json=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return _MockResponse()

    async def aclose(self):
        return None


async def test_report_nudge_sends_every_dimension(clean_env):
    clean_env.setenv("SUPAFONE_LABS_API_KEY", "sl_live_t")
    clean_env.setenv("SUPAFONE_LABS_API_BASE", "https://cloud.example.com/v1")
    client = _MockClient()
    ok = await report_nudge(
        session_id="call_1", provider="ultravox", text="Acknowledge the injury.",
        confidence=0.82, injected=True, kind="mixed", language="es",
        emotion="distressed", intent="fresh_injury_high_signup", urgency=0.8,
        latency_ms=412.5, model="claude-haiku-4-5-20251001", turns=7, client=client,
    )
    assert ok is True
    call = client.calls[0]
    assert call["url"] == "https://cloud.example.com/v1/events/nudge"
    assert call["headers"]["Authorization"] == "Bearer sl_live_t"
    payload = call["json"]
    for field, expected in {
        "session_id": "call_1", "provider": "ultravox", "confidence": 0.82,
        "injected": True, "kind": "mixed", "language": "es", "emotion": "distressed",
        "intent": "fresh_injury_high_signup", "urgency": 0.8, "latency_ms": 412.5,
        "model": "claude-haiku-4-5-20251001", "turns": 7,
    }.items():
        assert payload[field] == expected, field


async def test_no_license_means_no_telemetry(clean_env):
    client = _MockClient()
    ok = await report_nudge(session_id="c", provider="p", text="x", client=client)
    assert ok is False and client.calls == []


async def test_telemetry_can_be_disabled_by_env(clean_env):
    clean_env.setenv("SUPAFONE_LABS_API_KEY", "sl_live_t")
    clean_env.setenv("SUPAFONE_LABS_TELEMETRY", "off")
    client = _MockClient()
    ok = await report_nudge(session_id="c", provider="p", text="x", client=client)
    assert ok is False and client.calls == []


async def test_observe_schedules_full_granularity_nudge(clean_env, monkeypatch):
    clean_env.setenv("SUPAFONE_LABS_API_KEY", "sl_live_t")
    captured: list[dict] = []

    def fake_soon(**kwargs):
        captured.append(kwargs)

    monkeypatch.setattr("supafone_labs.telemetry.report_nudge_soon", fake_soon)
    brain = SupafoneLabs(
        provider="ultravox", oracle=OracleSession(provider=FakeLLMProvider()), mode="return"
    )
    await brain.observe(
        {"type": "transcript", "speaker": "caller", "final": True, "call_id": "c1",
         "text": "I was rear-ended at a red light yesterday and my neck hurts."}
    )
    assert captured, "observe() did not report a nudge"
    nudge = captured[0]
    assert nudge["session_id"] == "c1"
    assert nudge["provider"] == "ultravox"
    assert nudge["text"]
    assert nudge["confidence"] > 0
    assert nudge["emotion"] == "distressed"      # from the belief state
    assert nudge["latency_ms"] >= 0
    assert nudge["turns"] >= 1
    assert nudge["model"]


async def test_inject_via_taps_one_platform_whispers_to_another(clean_env):
    """The real-world combo: transcripts from the Deepgram tap, injection into Ultravox."""
    brain = SupafoneLabs(
        provider="deepgram",
        inject_via="ultravox",
        oracle=OracleSession(provider=FakeLLMProvider()),
        mode="return",
    )
    result = await brain.observe(
        {
            "type": "Results",
            "channel": {"alternatives": [{"transcript": "I was rear-ended yesterday."}]},
            "is_final": True,
            "speaker": "caller",
            "session_id": "c9",
        }
    )
    assert result.actions, "no action compiled"
    assert result.actions[0].provider == "ultravox"
    assert result.actions[0].kind == "inject_message"


async def test_report_nudge_soon_never_raises_without_loop(clean_env):
    clean_env.setenv("SUPAFONE_LABS_API_KEY", "sl_live_t")
    from supafone_labs.telemetry import report_nudge_soon

    # Called from sync context with a running loop: schedules quietly.
    report_nudge_soon(session_id="c", provider="p", text="x")
    await asyncio.sleep(0)  # let the scheduled task run (it will fail silently — no server)
