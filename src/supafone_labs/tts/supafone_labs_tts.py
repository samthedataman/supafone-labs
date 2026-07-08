"""SupafoneLabsTTS — Supafone Labs' own TTS provider, tier-aware with fallback.

One voice surface for both tiers:

* **Pro** (``SUPAFONE_LABS_API_KEY`` set): synthesizes on the hosted endpoint with
  Supafone Labs' own voice keys.
* **Free**: routes to the first BYO backend with a key — Deepgram Aura, then
  Cartesia Sonic, then ElevenLabs, then Inworld.
* **No keys at all**: the offline ``FakeTTSProvider``, so ``synthesize`` always
  returns playable audio.

A backend failure degrades down the same chain instead of raising — voicing a
whisper must never take down the call path it is coaching.
"""
from __future__ import annotations

from typing import Any

from supafone_labs.tiers import Tier, current_tier
from supafone_labs.tts.base import FakeTTSProvider, TTSProvider
from supafone_labs.tts.cartesia_tts import CartesiaTTSProvider
from supafone_labs.tts.deepgram_tts import DeepgramTTSProvider
from supafone_labs.tts.elevenlabs_tts import ElevenLabsTTSProvider
from supafone_labs.tts.hosted_tts import HostedTTSProvider
from supafone_labs.tts.inworld_tts import InworldTTSProvider


class SupafoneLabsTTS:
    """The default voice of SupafoneLabs: hosted when licensed, BYO-key otherwise."""

    provider_name = "supafone-labs"

    def __init__(
        self,
        voice: str | None = None,
        client: Any = None,
        backends: list[TTSProvider] | None = None,
    ) -> None:
        self.voice = voice
        if backends is not None:
            self._backends = list(backends)
        else:
            chain: list[TTSProvider] = []
            if current_tier() is Tier.PRO:
                chain.append(HostedTTSProvider(voice=voice, client=client))
            for backend in (
                DeepgramTTSProvider(client=client),
                CartesiaTTSProvider(client=client),
                ElevenLabsTTSProvider(client=client),
                InworldTTSProvider(client=client),
            ):
                if backend.enabled:
                    chain.append(backend)
            chain.append(FakeTTSProvider())
            self._backends = chain

    @property
    def active_backend(self) -> TTSProvider:
        return self._backends[0]

    async def synthesize(self, text: str, *, voice: str | None = None, **kwargs: Any) -> bytes:
        last_error: Exception | None = None
        for backend in self._backends:
            try:
                return await backend.synthesize(text, voice=voice or self.voice, **kwargs)
            except Exception as exc:  # degrade down the chain, never up the stack
                last_error = exc
        if last_error is not None:  # pragma: no cover - Fake never raises
            raise last_error
        return b""

    async def speak_directive(self, directive: Any, **kwargs: Any) -> bytes:
        """Voice a Directive (or any object with composed_text()) — e.g. a supervisor whisper."""
        text = directive.composed_text() if hasattr(directive, "composed_text") else str(directive)
        return await self.synthesize(text, **kwargs)
