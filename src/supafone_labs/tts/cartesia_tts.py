"""Cartesia Sonic TTS — the default Supafone Labs voice backend.

``POST https://api.cartesia.ai/tts/bytes`` with bearer authentication and a
``Cartesia-Version`` header; the JSON body names the model, transcript, voice
id and output format; the response body is the audio bytes.
"""
from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from supafone_labs.tts.http_base import HttpTTSBase

DEFAULT_MODEL = "sonic-3"
DEFAULT_VOICE = "db6b0ed5-d5d3-463d-ae85-518a07d3c2b4"  # Skylar - Friendly Guide
CARTESIA_VERSION = "2026-03-01"

MANAGED_VOICE_ALIASES = {
    "supafone-labs-calm-en",
    "supafone-labs-warm-en",
    "supafone-labs-direct-en",
}


def normalize_cartesia_voice(voice: str | None, fallback: str = DEFAULT_VOICE) -> str:
    """Return a valid Cartesia UUID and never forward another vendor's id."""
    candidate = str(voice or "").strip()
    if candidate.lower().startswith("cartesia:"):
        candidate = candidate.split(":", 1)[1].strip()
    if not candidate or candidate in MANAGED_VOICE_ALIASES:
        return fallback
    try:
        return str(UUID(candidate))
    except (ValueError, AttributeError, TypeError):
        return fallback


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
        self.voice = normalize_cartesia_voice(voice or os.getenv("CARTESIA_VOICE_ID"))
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
        voice_id = normalize_cartesia_voice(voice, self.voice)
        body["voice"] = {"id": voice_id}
        return await self._post_bytes(
            "https://api.cartesia.ai/tts/bytes",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Cartesia-Version": CARTESIA_VERSION,
            },
            json=body,
        )
