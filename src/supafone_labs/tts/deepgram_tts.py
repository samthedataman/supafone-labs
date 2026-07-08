"""Deepgram Aura TTS — free-tier BYO-key backend (verified against the live API).

``POST https://api.deepgram.com/v1/speak?model=<voice>&encoding=linear16&container=wav``
with ``Authorization: Token <DEEPGRAM_API_KEY>`` and ``{"text": ...}`` returns
16-bit mono WAV bytes.
"""
from __future__ import annotations

import os
from typing import Any

from supafone_labs.tts.http_base import HttpTTSBase

DEFAULT_VOICE = "aura-2-thalia-en"


class DeepgramTTSProvider(HttpTTSBase):
    provider_name = "deepgram"

    def __init__(
        self,
        api_key: str | None = None,
        voice: str | None = None,
        client: Any = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(client=client, timeout=timeout)
        self._api_key = (api_key or os.getenv("DEEPGRAM_API_KEY") or "").strip()
        self.voice = voice or os.getenv("SUPAFONE_LABS_TTS_VOICE") or DEFAULT_VOICE

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    async def synthesize(self, text: str, *, voice: str | None = None, **kwargs: Any) -> bytes:
        if not self._api_key:
            raise RuntimeError("DeepgramTTSProvider requires DEEPGRAM_API_KEY")
        return await self._post_bytes(
            "https://api.deepgram.com/v1/speak",
            params={
                "model": voice or self.voice,
                "encoding": "linear16",
                "container": "wav",
            },
            headers={"Authorization": f"Token {self._api_key}"},
            json={"text": str(text or "")},
        )
