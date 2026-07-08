"""Post-call scoring + the self-improvement loop wiring (auto-report, standing fetch)."""
from __future__ import annotations

import pytest

from supafone_labs import SupafoneLabs
from supafone_labs.llm import FakeLLMProvider
from supafone_labs.oracle.session import OracleSession
from supafone_labs.postcall import score_call
from supafone_labs.runtime.core.events import EventTypes, make_event
from supafone_labs.runtime.core.state import apply_events, build_initial_state


@pytest.fixture
def clean_env(monkeypatch):
    monkeypatch.delenv("SUPAFONE_LABS_API_KEY", raising=False)
    monkeypatch.delenv("SUPAFONE_LABS_TELEMETRY", raising=False)
    return monkeypatch


def _ev(event_type, session="c1", **kwargs):
    return make_event(event_type, session_id=session, provider="ultravox", **kwargs)


def test_clean_call_scores_one():
    state = build_initial_state(provider="ultravox", session_id="c1")
    state = apply_events(
        [_ev(EventTypes.CALLER_TRANSCRIPT_FINAL, actor="caller", text="hi")], state
    )
    report = score_call(state)
    assert report.score == 1.0
    assert report.outcome == "clean"
    assert report.summary == "clean call"


def test_unverified_booking_and_claims_are_penalized():
    state = build_initial_state(provider="ultravox", session_id="c1")
    events = [
        _ev(EventTypes.CALLER_TRANSCRIPT_FINAL, actor="caller", text="book me please"),
        _ev(EventTypes.TOOL_CALLED, actor="tool", data={"tool_name": "book_appointment"}),
        # no successful tool result: booking_requested but never verified
    ]
    state = apply_events(events, state)
    state.truth_state.last_unverified_claims = ["you're booked for Tuesday"]
    report = score_call(state, nudges=3, agent="intake")
    assert report.score < 0.5
    assert report.outcome == "issues"
    assert "booking was requested" in report.summary
    assert "end-of-call claims" in report.summary
    assert report.agent == "intake" and report.nudges == 3


def test_language_comes_from_last_tagged_caller_turn():
    state = build_initial_state(provider="deepgram", session_id="c1")
    events = [
        _ev(EventTypes.CALLER_TRANSCRIPT_FINAL, actor="caller", text="hola", data={"language": "es"}),
        _ev(EventTypes.AGENT_TRANSCRIPT_FINAL, actor="agent", text="hello"),
    ]
    state = apply_events(events, state)
    assert score_call(state).language == "es"


async def test_session_end_auto_reports_the_call(clean_env, monkeypatch):
    clean_env.setenv("SUPAFONE_LABS_API_KEY", "sl_live_t")
    sent: list[dict] = []
    monkeypatch.setattr("supafone_labs.telemetry.report_call_soon", lambda **kw: sent.append(kw))

    brain = SupafoneLabs(
        provider="ultravox",
        oracle=OracleSession(provider=FakeLLMProvider()),
        mode="return",
        agent_label="intake",
    )
    await brain.observe(
        {"type": "transcript", "speaker": "caller", "text": "I was rear-ended.", "final": True, "call_id": "c1"}
    )
    assert not sent  # not ended yet
    await brain.observe({"type": "call.ended", "call_id": "c1"})
    assert sent, "session end did not auto-report"
    report = sent[0]
    assert report["session_id"] == "c1"
    assert report["agent"] == "intake"
    assert report["nudges"] >= 1  # the earlier turn produced a whisper
    assert 0.0 <= report["score"] <= 1.0


async def test_brain_report_is_available_locally(clean_env):
    brain = SupafoneLabs(
        provider="ultravox", oracle=OracleSession(provider=FakeLLMProvider()), mode="return"
    )
    await brain.observe(
        {"type": "transcript", "speaker": "caller", "text": "hello", "final": True, "call_id": "c9"}
    )
    report = brain.report("c9")
    assert report is not None and report.turns >= 1
    assert brain.report("nonexistent") is None


async def test_standing_directive_folds_into_oracle_prompts(clean_env, monkeypatch):
    clean_env.setenv("SUPAFONE_LABS_API_KEY", "sl_live_t")

    async def fake_fetch(agent="default", client=None):
        assert agent == "intake"
        return "Never quote fees.\nAcknowledge injury before logistics."

    monkeypatch.setattr("supafone_labs.telemetry.fetch_standing", fake_fetch)
    brain = SupafoneLabs(
        provider="ultravox",
        oracle=OracleSession(provider=FakeLLMProvider()),
        mode="return",
        agent_label="intake",
    )
    await brain.observe(
        {"type": "transcript", "speaker": "caller", "text": "hi", "final": True, "call_id": "c1"}
    )
    assert "Never quote fees." in brain.oracle.directive_gen.system_prompt
    assert "Standing directive" in brain.oracle.belief_engine.system_prompt


async def test_no_telemetry_means_no_standing_fetch(clean_env, monkeypatch):
    called = []

    async def fake_fetch(agent="default", client=None):  # pragma: no cover
        called.append(agent)
        return "x"

    monkeypatch.setattr("supafone_labs.telemetry.fetch_standing", fake_fetch)
    brain = SupafoneLabs(
        provider="ultravox", oracle=OracleSession(provider=FakeLLMProvider()),
        mode="return", telemetry=False,
    )
    await brain.observe(
        {"type": "transcript", "speaker": "caller", "text": "hi", "final": True, "call_id": "c1"}
    )
    assert called == []
