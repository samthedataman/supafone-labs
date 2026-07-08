"""Cartesia Sonic TTS — free-tier BYO-key backend.

``POST https://api.cartesia.ai/tts/bytes`` with ``X-API-Key`` and a
``Cartesia-Version`` header; the JSON body names the model, transcript, voice
id and output format; the response body is the audio bytes.
"""
from __future__ import annotations

import os
from typing import Any

from supafone_labs.tts.http_base import HttpTTSBase

DEFAULT_MODEL = "sonic-2"
CARTESIA_VERSION = "2025-04-16"


class CartesiaTTSProvider(HttpTTSBase):
    provider_name = "cartesia"

    def __init__(
        self,
        api_key: str | None = None,
        voice: str | None = None,
        model: str = DEFAULT_MODEL,
        client: Any = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(client=client, timeout=timeout)
        self._api_key = (api_key or os.getenv("CARTESIA_API_KEY") or "").strip()
        self.voice = voice or os.getenv("CARTESIA_VOICE_ID") or ""
        self.model = model

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    async def synthesize(self, text: str, *, voice: str | None = None, **kwargs: Any) -> bytes:
        if not self._api_key:
            raise RuntimeError("CartesiaTTSProvider requires CARTESIA_API_KEY")
        body: dict[str, Any] = {
            "model_id": self.model,
            "transcript": str(text or ""),
            "output_format": {
                "container": "wav",
                "encoding": "pcm_s16le",
                "sample_rate": 16000,
            },
        }
        voice_id = voice or self.voice
        if voice_id:
            body["voice"] = {"mode": "id", "id": voice_id}
        return await self._post_bytes(
            "https://api.cartesia.ai/tts/bytes",
            headers={
                "X-API-Key": self._api_key,
                "Cartesia-Version": CARTESIA_VERSION,
            },
            json=body,
        )
