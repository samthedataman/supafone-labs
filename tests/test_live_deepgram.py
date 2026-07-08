"""LIVE Deepgram checks — run only when DEEPGRAM_API_KEY is set (network + key).

These prove the real API still speaks the shapes our DeepgramAdapter and
DeepgramTTSProvider are built against:

* ``POST /v1/listen`` (nova-3) returns ``results.channels[].alternatives[]``
  with a transcript — the same alternatives shape the streaming ``Results``
  messages carry, which ``DeepgramAdapter._parse_stt_results`` consumes.
* ``POST /v1/speak`` (aura-2) returns playable WAV bytes via our own
  ``DeepgramTTSProvider``.

Run: ``DEEPGRAM_API_KEY=... pytest tests/test_live_deepgram.py -m live``
"""
from __future__ import annotations

import io
import os
import wave

import pytest

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not os.getenv("DEEPGRAM_API_KEY"), reason="DEEPGRAM_API_KEY not set"),
]

SAMPLE_AUDIO_URL = "https://dpgr.am/spacewalk.wav"


async def test_live_stt_prerecorded_matches_adapter_shape():
    httpx = pytest.importorskip("httpx")
    from supafone_labs.runtime.adapters import DeepgramAdapter
    from supafone_labs.runtime.core.events import EventTypes

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.deepgram.com/v1/listen",
            params={"model": "nova-3", "smart_format": "true"},
            headers={"Authorization": f"Token {os.environ['DEEPGRAM_API_KEY']}"},
            json={"url": SAMPLE_AUDIO_URL},
        )
    resp.raise_for_status()
    data = resp.json()
    alternatives = data["results"]["channels"][0]["alternatives"]
    assert alternatives and alternatives[0]["transcript"].strip()

    # Feed the live alternatives back through the adapter as a streaming
    # Results message — the adapter must tap it as caller speech.
    events = await DeepgramAdapter().parse_event(
        {
            "type": "Results",
            "channel": {"alternatives": alternatives},
            "is_final": True,
            "session_id": "live_1",
        }
    )
    assert events and events[0].type == EventTypes.CALLER_TRANSCRIPT_FINAL
    assert events[0].text == alternatives[0]["transcript"].strip()


async def test_live_tts_aura_returns_playable_wav():
    pytest.importorskip("httpx")
    from supafone_labs.tts import DeepgramTTSProvider

    provider = DeepgramTTSProvider()
    assert provider.enabled
    audio = await provider.synthesize("Supafone Labs live text to speech check.")
    with wave.open(io.BytesIO(audio), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getnframes() > 0


async def test_live_supafone_labs_tts_routes_to_deepgram_on_free_tier(monkeypatch):
    pytest.importorskip("httpx")
    monkeypatch.delenv("SUPAFONE_LABS_API_KEY", raising=False)
    from supafone_labs.tts import DeepgramTTSProvider, SupafoneLabsTTS

    tts = SupafoneLabsTTS()
    assert isinstance(tts.active_backend, DeepgramTTSProvider)
    audio = await tts.synthesize("Routing through my own voice.")
    assert isinstance(audio, bytes) and len(audio) > 1000
