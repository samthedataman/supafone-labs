"""DeepgramLiveSTT — the live multilingual transcription tap.

One streaming websocket per audio track (caller / agent), modeled on the
production Twilio-fork consumer proven in MediVoice. Each Deepgram ``Results``
message is normalized into exactly the raw-event shape ``DeepgramAdapter``
parses (``channel.alternatives``, ``is_final``/``speech_final``, ``languages``,
plus our ``speaker`` and ``session_id`` tags) and handed to ``on_event`` —
usually ``brain.observe(raw, provider="deepgram")``.

Degrade-safe by construction: no API key -> ``send`` no-ops; connect/read
failures are swallowed after logging; nothing here can take down the call
whose audio it is shadowing. ``websockets`` is imported lazily (extra:
``pip install supafone-labs[stt]``); tests inject a fake connector.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from typing import Any, Awaitable, Callable, Optional
from urllib.parse import urlencode

from supafone_labs.llm.hosted_provider import DEFAULT_API_BASE
from supafone_labs.stt.language import STTMode, choose_language_mode
from supafone_labs.tiers import license_key

logger = logging.getLogger("supafone_labs.stt")

RawEventHandler = Callable[[dict], Awaitable[Any]]


class DeepgramLiveSTT:
    """One Deepgram streaming-STT websocket for one speaker track."""

    def __init__(
        self,
        on_event: RawEventHandler,
        *,
        session_id: str,
        speaker: str = "caller",
        api_key: Optional[str] = None,
        mode: Optional[STTMode] = None,
        encoding: str = "linear16",
        sample_rate: int = 16000,
        interim_results: bool = True,
        connect: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.on_event = on_event
        self.session_id = session_id
        self.speaker = speaker
        self._api_key = (api_key or os.getenv("DEEPGRAM_API_KEY") or "").strip()
        self.mode = mode or choose_language_mode(None)
        self.encoding = encoding
        self.sample_rate = sample_rate
        self.interim_results = interim_results
        self._connect = connect  # test seam: async factory(url, headers) -> ws
        self._ws: Any = None
        self._last_ws: Any = None  # survives reader teardown so close() can reach it
        self._reader_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._closed = False

    @property
    def enabled(self) -> bool:
        # BYO Deepgram key, injected test socket, or a Supafone Labs pro license
        # (routed through the hosted live-STT proxy) all light this up.
        return bool(self._api_key) or self._connect is not None or bool(license_key())

    def _params(self) -> dict[str, str]:
        return {
            "model": self.mode.model,
            "language": self.mode.language,
            "encoding": self.encoding,
            "sample_rate": str(self.sample_rate),
            "channels": "1",
            "interim_results": "true" if self.interim_results else "false",
            "smart_format": "true",
            "punctuate": "true",
        }

    def _endpoint(self) -> tuple[str, dict[str, str]]:
        params = self._params()
        if self._api_key:
            return (
                f"wss://api.deepgram.com/v1/listen?{urlencode(params)}",
                {"Authorization": f"Token {self._api_key}"},
            )
        lic = license_key()
        if lic:  # pro tier: Supafone Labs' hosted proxy, zero Deepgram account
            base = (os.getenv("SUPAFONE_LABS_API_BASE") or DEFAULT_API_BASE).rstrip("/")
            ws_base = base.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
            params["api_key"] = lic
            return f"{ws_base}/stt/live?{urlencode(params)}", {}
        return f"wss://api.deepgram.com/v1/listen?{urlencode(params)}", {}

    def _url(self) -> str:
        return self._endpoint()[0]

    async def _open(self) -> None:
        if self._ws is not None or self._closed or not self.enabled:
            return
        async with self._lock:
            if self._ws is not None:
                return
            url, headers = self._endpoint()
            if self._connect is not None:
                self._ws = await self._connect(url, headers)
            else:
                try:
                    import websockets
                except ImportError as exc:
                    raise RuntimeError(
                        "DeepgramLiveSTT requires the 'stt' extra: pip install supafone-labs[stt]"
                    ) from exc
                try:
                    self._ws = await websockets.connect(
                        url, additional_headers=headers, ping_interval=20, ping_timeout=20
                    )
                except TypeError:  # older websockets builds
                    self._ws = await websockets.connect(
                        url, extra_headers=headers, ping_interval=20, ping_timeout=20
                    )
            self._last_ws = self._ws
            self._reader_task = asyncio.create_task(self._reader())

    async def _reader(self) -> None:
        ws = self._ws
        if ws is None:
            return
        try:
            async for message in ws:
                if isinstance(message, (bytes, bytearray)):
                    continue
                try:
                    data = json.loads(message)
                except Exception:
                    continue
                alternatives = ((data.get("channel") or {}).get("alternatives")) or [{}]
                if not str((alternatives[0] or {}).get("transcript") or "").strip():
                    continue
                raw = {
                    **data,
                    "type": data.get("type") or "Results",
                    "speaker": self.speaker,
                    "session_id": self.session_id,
                }
                try:
                    await self.on_event(raw)
                except Exception:
                    logger.debug("stt on_event handler failed", exc_info=True)
        except Exception as exc:
            if not self._closed:
                logger.warning("Deepgram live STT reader ended (%s): %s", self.speaker, exc)
        finally:
            self._ws = None

    async def send(self, audio: bytes) -> None:
        """Stream one chunk of raw audio. No-ops without a key; never raises."""
        if self._closed or not audio or not self.enabled:
            return
        try:
            await self._open()
            if self._ws is not None:
                await self._ws.send(audio)
        except Exception as exc:
            logger.warning("Deepgram live STT send failed (%s): %s", self.speaker, exc)

    async def send_b64(self, payload_b64: str) -> None:
        """Convenience for Twilio-style base64 media frames."""
        if payload_b64:
            try:
                await self.send(base64.b64decode(payload_b64))
            except Exception:
                logger.debug("invalid base64 media frame dropped", exc_info=True)

    async def finalize(self) -> None:
        """Ask Deepgram to flush pending audio into final results."""
        try:
            if self._ws is not None:
                await self._ws.send(json.dumps({"type": "Finalize"}))
        except Exception:
            pass

    async def close(self) -> None:
        self._closed = True
        ws = self._ws or self._last_ws
        self._ws = self._last_ws = None
        if ws is not None:
            try:
                await ws.send(json.dumps({"type": "CloseStream"}))
            except Exception:
                pass
            try:
                await ws.close()
            except Exception:
                pass
        if self._reader_task is not None:
            self._reader_task.cancel()
            self._reader_task = None


# Track spellings from Twilio / the sales-dialer fork -> conversational speaker.
_TRACK_SPEAKER = {
    "inbound": "caller",
    "inbound_track": "caller",
    "caller": "caller",
    "user": "caller",
    "outbound": "agent",
    "outbound_track": "agent",
    "agent": "agent",
}


class MultilingualCallTap:
    """Two-track live tap for one call: fork both sides' audio, get language-tagged
    canonical transcripts flowing into a Supafone Labs brain.

    Usage (Twilio media stream, S2S audio fork, or any raw source)::

        tap = MultilingualCallTap(brain, session_id=call_sid)
        await tap.feed(track="inbound", payload_b64=frame)   # per media frame
        await tap.close()                                     # on hangup

    The brain sees ``deepgram`` Results events with per-utterance ``languages``
    (nova-3 multi), so BeliefState.language, directive language mirroring, and
    the Spanish guardrail translations all light up automatically.
    """

    def __init__(
        self,
        brain: Any,
        *,
        session_id: str,
        preferred_languages: Optional[list[str]] = None,
        api_key: Optional[str] = None,
        encoding: str = "mulaw",
        sample_rate: int = 8000,
        connect: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.brain = brain
        self.session_id = session_id
        self.mode = choose_language_mode(preferred_languages)
        self._kwargs = dict(
            api_key=api_key, mode=self.mode, encoding=encoding, sample_rate=sample_rate, connect=connect
        )
        self._tracks: dict[str, DeepgramLiveSTT] = {}
        self._closed = False

    async def _observe(self, raw: dict) -> None:
        await self.brain.observe(raw, provider="deepgram")

    def _consumer(self, track: Any) -> DeepgramLiveSTT:
        speaker = _TRACK_SPEAKER.get(str(track).strip().lower(), "caller")
        consumer = self._tracks.get(speaker)
        if consumer is None:
            consumer = DeepgramLiveSTT(
                self._observe, session_id=self.session_id, speaker=speaker, **self._kwargs
            )
            self._tracks[speaker] = consumer
        return consumer

    async def feed(self, *, track: Any, audio: bytes = b"", payload_b64: str = "") -> None:
        if self._closed:
            return
        consumer = self._consumer(track)
        if payload_b64:
            await consumer.send_b64(payload_b64)
        elif audio:
            await consumer.send(audio)

    async def close(self) -> None:
        self._closed = True
        for consumer in list(self._tracks.values()):
            await consumer.close()
        self._tracks.clear()
