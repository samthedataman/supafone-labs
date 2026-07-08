"""Inworld TTS — free-tier BYO-key backend (verified against the live API).

``POST https://api.inworld.ai/tts/v1/voice`` with ``Authorization: Basic
<INWORLD_API_KEY>`` and ``{"text", "voiceId", "modelId"}`` returns JSON whose
``audioContent`` is base64-encoded audio.
"""
from __future__ import annotations

import base64
import os
from typing import Any

DEFAULT_VOICE = "Ashley"
DEFAULT_MODEL = "inworld-tts-1"


class InworldTTSProvider:
    provider_name = "inworld"

    def __init__(
        self,
        api_key: str | None = None,
        voice: str | None = None,
        model: str = DEFAULT_MODEL,
        client: Any = None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = (api_key or os.getenv("INWORLD_API_KEY") or "").strip()
        self.voice = voice or os.getenv("INWORLD_VOICE_ID") or DEFAULT_VOICE
        self.model = model
        self._client = client
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    async def synthesize(self, text: str, *, voice: str | None = None, **kwargs: Any) -> bytes:
        if not self._api_key:
            raise RuntimeError("InworldTTSProvider requires INWORLD_API_KEY")
        client = self._client
        owns_client = client is None
        if owns_client:
            try:
                import httpx
            except ImportError as exc:  # pragma: no cover - exercised only without the extra
                raise RuntimeError(
                    "InworldTTSProvider requires the 'http' extra: pip install supafone-labs[http]"
                ) from exc
            client = httpx.AsyncClient(timeout=self.timeout)
        try:
            resp = await client.post(
                "https://api.inworld.ai/tts/v1/voice",
                headers={"Authorization": f"Basic {self._api_key}"},
                json={
                    "text": str(text or ""),
                    "voiceId": voice or self.voice,
                    "modelId": self.model,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return base64.b64decode(data.get("audioContent") or b"")
        finally:
            if owns_client:
                await client.aclose()
