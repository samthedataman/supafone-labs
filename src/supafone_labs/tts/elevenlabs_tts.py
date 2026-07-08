"""ElevenLabs TTS — free-tier BYO-key backend.

``POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`` with an
``xi-api-key`` header; the response body is the audio bytes.
"""
from __future__ import annotations

import os
from typing import Any

from supafone_labs.tts.http_base import HttpTTSBase

DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"  # "Rachel", ElevenLabs' public default
DEFAULT_MODEL = "eleven_turbo_v2_5"


class ElevenLabsTTSProvider(HttpTTSBase):
    provider_name = "elevenlabs"

    def __init__(
        self,
        api_key: str | None = None,
        voice: str | None = None,
        model: str = DEFAULT_MODEL,
        client: Any = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(client=client, timeout=timeout)
        self._api_key = (api_key or os.getenv("ELEVENLABS_API_KEY") or "").strip()
        self.voice = voice or os.getenv("ELEVENLABS_VOICE_ID") or DEFAULT_VOICE
        self.model = model

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    async def synthesize(self, text: str, *, voice: str | None = None, **kwargs: Any) -> bytes:
        if not self._api_key:
            raise RuntimeError("ElevenLabsTTSProvider requires ELEVENLABS_API_KEY")
        voice_id = voice or self.voice
        return await self._post_bytes(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": self._api_key},
            json={"text": str(text or ""), "model_id": self.model},
        )
