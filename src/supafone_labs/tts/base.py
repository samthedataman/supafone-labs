"""TTS provider contract + a deterministic offline fake.

A ``TTSProvider`` turns text into audio bytes. SupafoneLabs uses it to *voice*
oracle output — e.g. whisper a directive into a supervisor's ear, read a
call-summary aloud, or serve as the speech engine for a pipeline stack
(Pipecat/LiveKit) that wants SupafoneLabs as its TTS component.

``FakeTTSProvider`` needs no key and no network: it renders a soft sine-tone
WAV whose duration tracks the text length, so demos and tests produce real,
playable audio deterministically.
"""
from __future__ import annotations

import io
import math
import struct
import wave
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TTSProvider(Protocol):
    """Anything that can synthesize text into audio bytes."""

    provider_name: str

    async def synthesize(self, text: str, *, voice: str | None = None, **kwargs: Any) -> bytes: ...


class FakeTTSProvider:
    """Offline, deterministic TTS: a soft sine tone sized to the text. Valid WAV."""

    provider_name = "fake"

    def __init__(self, sample_rate: int = 16000, frequency: float = 440.0) -> None:
        self.sample_rate = sample_rate
        self.frequency = frequency

    async def synthesize(self, text: str, *, voice: str | None = None, **kwargs: Any) -> bytes:
        words = max(1, len(str(text or "").split()))
        seconds = min(10.0, 0.3 * words)  # ~0.3s per word, capped
        n_frames = int(self.sample_rate * seconds)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            amplitude = 8000
            frames = bytearray()
            for i in range(n_frames):
                # gentle fade in/out so the tone doesn't click
                envelope = min(1.0, i / 800, (n_frames - i) / 800)
                sample = int(
                    amplitude * envelope * math.sin(2 * math.pi * self.frequency * i / self.sample_rate)
                )
                frames += struct.pack("<h", sample)
            wav.writeframes(bytes(frames))
        return buf.getvalue()
