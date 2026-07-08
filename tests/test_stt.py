"""supafone_labs.stt — language-mode resolution, the combination matrix, and the
live tap wired end-to-end into a brain (fake websocket, no network)."""
from __future__ import annotations

import asyncio
import json

from supafone_labs import SupafoneLabs
from supafone_labs.llm import FakeLLMProvider
from supafone_labs.oracle.session import OracleSession
from supafone_labs.stt import (
    DeepgramLiveSTT,
    MultilingualCallTap,
    choose_language_mode,
    needs_deepgram_tap,
    recommended_setup,
)

SPANISH_TEXT = "Hola, tuve un accidente de coche ayer y me duele el cuello."


# --- language-mode resolution ------------------------------------------------------

def test_default_mode_is_nova3_multi_code_switching():
    mode = choose_language_mode(None)
    assert mode.model == "nova-3"
    assert mode.language == "multi"
    assert mode.code_switching


def test_multi_set_languages_stay_code_switching():
    mode = choose_language_mode(["en", "es"])
    assert mode.language == "multi" and mode.code_switching


def test_single_pinned_language_goes_mono():
    mode = choose_language_mode(["es"])
    assert mode.language == "es" and not mode.code_switching
    assert mode.model == "nova-3"


def test_language_outside_multi_set_falls_back():
    mode = choose_language_mode(["tr"])
    assert mode.language == "tr" and mode.model == "nova-2"


def test_uncoverable_combination_pins_primary_with_note():
    mode = choose_language_mode(["tr", "en"])
    assert mode.language == "tr" and not mode.code_switching
    assert "exceed" in mode.notes


def test_language_names_normalize():
    assert choose_language_mode(["Spanish"]).language == "es"


# --- the combination matrix ---------------------------------------------------------

def test_transcript_streaming_providers_skip_the_tap():
    for provider in ("ultravox", "vapi", "elevenlabs", "retell", "livekit"):
        assert not needs_deepgram_tap(provider)
        rec = recommended_setup(provider)
        assert rec.transcript_source == "provider" and not rec.run_deepgram_tap


def test_audio_only_sources_require_the_tap():
    for provider in ("twilio", "raw_audio", "some_unknown_stack"):
        assert needs_deepgram_tap(provider)
        rec = recommended_setup(provider)
        assert rec.run_deepgram_tap and rec.transcript_source == "deepgram_tap"


def test_multilingual_promotes_tap_to_language_authority():
    rec = recommended_setup("ultravox", multilingual=True)
    assert rec.run_deepgram_tap
    assert rec.transcript_source == "deepgram_tap"  # single source — never both
    assert rec.language_source == "deepgram_tap"
    assert "double ingestion" in rec.notes


def test_multilingual_without_audio_access_degrades_to_heuristics():
    rec = recommended_setup("vapi", multilingual=True)
    assert not rec.run_deepgram_tap
    assert rec.language_source == "oracle_heuristics"


def test_deepgram_voice_agent_is_already_language_tagged():
    rec = recommended_setup("deepgram", multilingual=True)
    assert not rec.run_deepgram_tap
    assert rec.language_source == "provider"


# --- the live tap (fake websocket) ----------------------------------------------------

def _results_message(text: str, language: str, *, is_final: bool = True) -> str:
    return json.dumps(
        {
            "type": "Results",
            "channel": {"alternatives": [{"transcript": text, "confidence": 0.98}]},
            "is_final": is_final,
            "speech_final": is_final,
            "languages": [language],
        }
    )


class FakeWS:
    def __init__(self, messages: list[str]):
        self.messages = list(messages)
        self.sent: list = []
        self.closed = False

    async def send(self, data):
        self.sent.append(data)

    async def close(self):
        self.closed = True

    def __aiter__(self):
        async def gen():
            for message in self.messages:
                yield message

        return gen()


def _fake_connector(ws: FakeWS, seen_urls: list[str]):
    async def connect(url: str, headers: dict):
        seen_urls.append(url)
        return ws

    return connect


async def test_live_stt_normalizes_results_with_speaker_and_session():
    ws = FakeWS([_results_message(SPANISH_TEXT, "es")])
    urls: list[str] = []
    got: list[dict] = []

    async def collect(raw: dict):
        got.append(raw)

    stt = DeepgramLiveSTT(
        collect, session_id="call_1", speaker="caller", connect=_fake_connector(ws, urls)
    )
    await stt.send(b"\x00\x01")
    await asyncio.wait_for(stt._reader_task, timeout=2)

    assert "model=nova-3" in urls[0] and "language=multi" in urls[0]
    assert got, "no events surfaced from the fake stream"
    raw = got[0]
    assert raw["type"] == "Results"
    assert raw["speaker"] == "caller"
    assert raw["session_id"] == "call_1"
    assert raw["languages"] == ["es"]
    assert ws.sent == [b"\x00\x01"]


async def test_live_stt_without_key_is_a_safe_noop(monkeypatch):
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    monkeypatch.delenv("SUPAFONE_LABS_API_KEY", raising=False)

    async def collect(raw):  # pragma: no cover - must never fire
        raise AssertionError("no events expected")

    stt = DeepgramLiveSTT(collect, session_id="c", speaker="caller")
    assert not stt.enabled
    await stt.send(b"\x00")  # must not raise


async def test_pro_license_routes_tap_through_hosted_proxy(monkeypatch):
    """No Deepgram account + a Supafone Labs license -> the tap connects to the
    cloud's /v1/stt/live proxy instead of Deepgram directly."""
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    monkeypatch.setenv("SUPAFONE_LABS_API_KEY", "sl_live_test123")
    monkeypatch.setenv("SUPAFONE_LABS_API_BASE", "https://cloud.example.com/v1")

    async def collect(raw):
        pass

    stt = DeepgramLiveSTT(collect, session_id="c", speaker="caller")
    assert stt.enabled
    url, headers = stt._endpoint()
    assert url.startswith("wss://cloud.example.com/v1/stt/live?")
    assert "api_key=sl_live_test123" in url
    assert "language=multi" in url
    assert headers == {}


async def test_byo_deepgram_key_goes_direct(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dg_test")
    monkeypatch.setenv("SUPAFONE_LABS_API_KEY", "sl_live_test123")

    async def collect(raw):
        pass

    stt = DeepgramLiveSTT(collect, session_id="c", speaker="caller")
    url, headers = stt._endpoint()
    assert url.startswith("wss://api.deepgram.com/v1/listen?")
    assert headers["Authorization"] == "Token dg_test"


async def test_multilingual_tap_feeds_brain_and_language_reaches_directive():
    """Audio frames -> fake Deepgram (Spanish results) -> DeepgramAdapter ->
    state -> oracle: the caller's language must reach the directive."""
    caller_ws = FakeWS([_results_message(SPANISH_TEXT, "es")])
    agent_ws = FakeWS([_results_message("Thanks for calling, how can I help?", "en")])
    # Consumers are created in feed order: inbound (caller) first, then outbound.
    pending = [caller_ws, agent_ws]

    async def connect(url: str, headers: dict):
        return pending.pop(0)

    brain = SupafoneLabs(
        provider="deepgram", oracle=OracleSession(provider=FakeLLMProvider()), mode="return"
    )
    tap = MultilingualCallTap(brain, session_id="call_9", connect=connect)

    await tap.feed(track="inbound", audio=b"\x00")
    await tap.feed(track="outbound", audio=b"\x00")
    for consumer in tap._tracks.values():
        if consumer._reader_task is not None:
            await asyncio.wait_for(consumer._reader_task, timeout=2)

    state = brain._states.get("call_9")
    assert state is not None, "no state accumulated from tap events"
    caller_turns = [t for t in state.transcript if t.actor == "caller"]
    assert caller_turns and caller_turns[-1].language == "es"
    assert SPANISH_TEXT in caller_turns[-1].text

    # The oracle's language inference must pick up the tagged turn.
    directive = await brain.oracle.directive_gen.generate(
        brain.oracle.last_belief or __import__("supafone_labs").BeliefState(), state, ["No legal advice"]
    )
    assert directive.language == "es"

    await tap.close()
    assert caller_ws.closed and agent_ws.closed
