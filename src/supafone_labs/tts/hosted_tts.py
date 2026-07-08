"""Hosted TTS — the paid tier's voice backend (Supafone Labs' own keys).

``POST {SUPAFONE_LABS_API_BASE}/tts`` with the user's ``SUPAFONE_LABS_API_KEY``
license; the server synthesizes on Supafone Labs-managed voice keys and returns
audio bytes.
"""
from __future__ import annotations

import os
from typing import Any

from supafone_labs.tiers import TierError, license_key
from supafone_labs.tts.http_base import HttpTTSBase

DEFAULT_API_BASE = "https://api.labs.supafone.ai/v1"
DEFAULT_VOICE = "supafone-labs-calm-en"


class HostedTTSProvider(HttpTTSBase):
    provider_name = "hosted"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        voice: str | None = None,
        client: Any = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(client=client, timeout=timeout)
        self._api_key = (api_key or license_key()).strip()
        self.base_url = (base_url or os.getenv("SUPAFONE_LABS_API_BASE") or DEFAULT_API_BASE).rstrip("/")
        self.voice = voice or os.getenv("SUPAFONE_LABS_TTS_VOICE") or DEFAULT_VOICE

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    async def synthesize(self, text: str, *, voice: str | None = None, **kwargs: Any) -> bytes:
        if not self._api_key:
            raise TierError(
                "HostedTTSProvider needs a SUPAFONE_LABS_API_KEY (pro tier). "
                "On the free tier use your own keys: Deepgram, Cartesia, or ElevenLabs."
            )
        return await self._post_bytes(
            f"{self.base_url}/tts",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"text": str(text or ""), "voice": voice or self.voice, "format": "wav"},
        )
