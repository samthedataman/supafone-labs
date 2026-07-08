"""LIVE provider contract checks — each test needs that provider's key + network.

These are the receipts behind the adapter fixtures: every assertion here was
first observed as a real wire frame from the provider, then encoded in the
offline tests. Run: ``pytest -m live`` with keys in the environment.
"""
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.live

needs = lambda var: pytest.mark.skipif(not os.getenv(var), reason=f"{var} not set")  # noqa: E731


@needs("ULTRAVOX_API_KEY")
async def test_live_ultravox_rest_messages_parse():
    """Real Ultravox REST call messages (MESSAGE_ROLE_*) tap as transcript events."""
    httpx = pytest.importorskip("httpx")
    from supafone_labs.runtime.adapters import UltravoxAdapter
    from supafone_labs.runtime.core.events import EventTypes

    headers = {"X-API-Key": os.environ["ULTRAVOX_API_KEY"]}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            "https://api.ultravox.ai/api/calls", params={"pageSize": 1}, headers=headers
        )
        resp.raise_for_status()
        calls = resp.json().get("results") or []
        if not calls:
            pytest.skip("account has no calls to sample")
        resp = await client.get(
            f"https://api.ultravox.ai/api/calls/{calls[0]['callId']}/messages", headers=headers
        )
        resp.raise_for_status()
        messages = [m for m in resp.json().get("results") or [] if m.get("text")]
    assert messages, "expected at least one real transcript message"
    adapter = UltravoxAdapter()
    events = await adapter.parse_event(
        {"type": "transcript", "role": messages[0]["role"], "text": messages[0]["text"], "final": True}
    )
    assert events and events[0].type in {
        EventTypes.CALLER_TRANSCRIPT_FINAL,
        EventTypes.AGENT_TRANSCRIPT_FINAL,
    }
    assert events[0].text == messages[0]["text"]


@needs("ELEVENLABS_API_KEY")
@needs("ELEVENLABS_AGENT_ID")
async def test_live_elevenlabs_ws_frames_and_contextual_update():
    """Real ConvAI session: initiation frame parses; contextual_update (our whisper) is accepted."""
    import asyncio
    import json

    websockets = pytest.importorskip("websockets")
    from supafone_labs.runtime.adapters import ElevenLabsAdapter
    from supafone_labs.runtime.core.events import EventTypes

    url = (
        "wss://api.elevenlabs.io/v1/convai/conversation"
        f"?agent_id={os.environ['ELEVENLABS_AGENT_ID']}"
    )
    adapter = ElevenLabsAdapter()
    async with websockets.connect(
        url, additional_headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}
    ) as ws:
        first = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
        events = await adapter.parse_event(first)
        assert events and events[0].type == EventTypes.SESSION_STARTED
        assert events[0].provider_session_id.startswith("conv")

        # The whisper path: inject context, then force a turn. A malformed
        # injection would surface as an error/close instead of agent_response.
        await ws.send(json.dumps({"type": "contextual_update", "text": "live contract check"}))
        await ws.send(json.dumps({"type": "user_message", "text": "Hello?"}))
        saw_agent_response = False
        for _ in range(12):
            raw = await asyncio.wait_for(ws.recv(), timeout=30)
            if isinstance(raw, (bytes, bytearray)):
                continue
            frame = json.loads(raw)
            assert frame.get("type") not in {"error", "close"}, frame
            parsed = await adapter.parse_event(frame)
            if parsed and parsed[0].type == EventTypes.AGENT_TRANSCRIPT_FINAL:
                assert parsed[0].text
                saw_agent_response = True
                break
        assert saw_agent_response


@needs("CARTESIA_API_KEY")
@needs("DEEPGRAM_API_KEY")
async def test_live_cartesia_ink_stt_round_trip():
    """Deepgram TTS -> Cartesia Ink STT -> our adapter: full cross-provider audio loop."""
    import asyncio
    import io
    import json
    import wave

    websockets = pytest.importorskip("websockets")
    from supafone_labs.runtime.adapters import CartesiaAdapter
    from supafone_labs.runtime.core.events import EventTypes
    from supafone_labs.tts import DeepgramTTSProvider

    spoken = "The second mind is listening."
    audio = await DeepgramTTSProvider().synthesize(spoken)
    with wave.open(io.BytesIO(audio), "rb") as wav:
        rate = wav.getframerate()
        pcm = wav.readframes(wav.getnframes())

    url = (
        "wss://api.cartesia.ai/stt/websocket"
        f"?api_key={os.environ['CARTESIA_API_KEY']}&cartesia_version=2025-04-16"
        f"&model=ink-whisper&encoding=pcm_s16le&sample_rate={rate}"
    )
    transcript_frames = []
    async with websockets.connect(url) as ws:
        chunk = rate * 2 // 5
        for i in range(0, len(pcm), chunk):
            await ws.send(pcm[i : i + chunk])
        await ws.send("finalize")
        await ws.send("done")
        while True:
            frame = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
            if frame.get("type") == "transcript":
                transcript_frames.append(frame)
            if frame.get("type") in {"done", "error"}:
                assert frame.get("type") == "done", frame
                break

    assert transcript_frames, "Ink returned no transcript frames"
    adapter = CartesiaAdapter()
    events = await adapter.parse_event(transcript_frames[-1])
    assert events and events[0].type in {
        EventTypes.CALLER_TRANSCRIPT_FINAL,
        EventTypes.CALLER_TRANSCRIPT_PARTIAL,
    }
    assert "second mind" in events[0].text.lower()


@needs("DEEPGRAM_API_KEY")
async def test_live_multilingual_stt_tap_nova3_multi():
    """Deepgram TTS audio -> DeepgramLiveSTT (nova-3 language=multi) live:
    real Results frames must carry the transcript AND a language tag."""
    import asyncio
    import io
    import wave

    pytest.importorskip("websockets")
    from supafone_labs.stt import DeepgramLiveSTT
    from supafone_labs.tts import DeepgramTTSProvider

    spoken = "The second mind is listening to this call."
    audio = await DeepgramTTSProvider().synthesize(spoken)
    with wave.open(io.BytesIO(audio), "rb") as wav:
        rate = wav.getframerate()
        pcm = wav.readframes(wav.getnframes())

    got: list[dict] = []

    async def collect(raw: dict):
        got.append(raw)

    stt = DeepgramLiveSTT(
        collect, session_id="live_stt_1", speaker="caller", encoding="linear16", sample_rate=rate
    )
    chunk = rate * 2 // 5
    for _ in range(3):  # ~0.6s lead-in silence: streaming models garble cold starts
        await stt.send(b"\x00" * chunk)
    for i in range(0, len(pcm), chunk):
        await stt.send(pcm[i : i + chunk])
    for _ in range(10):  # ~2s trailing silence so endpointing can fire
        await stt.send(b"\x00" * chunk)
    await stt.finalize()

    PHRASE = "listening to this call"

    def final_text() -> str:
        return " ".join(
            ((r.get("channel") or {}).get("alternatives") or [{}])[0].get("transcript", "")
            for r in got
            if r.get("is_final") or r.get("speech_final")
        )

    for _ in range(60):  # up to ~15s for the full phrase to finalize
        if PHRASE in final_text().lower():
            break
        await asyncio.sleep(0.25)
    await stt.close()

    finals = [r for r in got if r.get("is_final") or r.get("speech_final")]
    assert finals, f"no final results (got {len(got)} frames)"
    assert PHRASE in final_text().lower(), f"final text: {final_text()!r}"
    assert all(r.get("speaker") == "caller" and r.get("session_id") == "live_stt_1" for r in got)

    # nova-3 multi tags language at alternatives[0].languages (streaming shape,
    # verified live) — and the adapter must surface it into event.data.
    from supafone_labs.runtime.adapters import DeepgramAdapter

    events = await DeepgramAdapter().parse_event(finals[-1])
    assert events and events[0].data.get("language") == "en"


@needs("INWORLD_API_KEY")
async def test_live_inworld_tts_returns_audio():
    pytest.importorskip("httpx")
    from supafone_labs.tts import InworldTTSProvider

    provider = InworldTTSProvider()
    assert provider.enabled
    audio = await provider.synthesize("Second mind live probe.")
    assert isinstance(audio, bytes) and len(audio) > 1000
