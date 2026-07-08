"""TTS provider resolution: explicit by name, or auto by tier and available keys."""
from __future__ import annotations

import os
from typing import Any

from supafone_labs.tiers import license_key
from supafone_labs.tts.base import FakeTTSProvider, TTSProvider


def get_tts_provider(name: str | None = None, **kwargs: Any) -> TTSProvider:
    """Return a TTS provider by name, or auto-resolve.

    Names: 'supafone_labs' (tier-aware front, the default), 'hosted', 'deepgram',
    'cartesia', 'elevenlabs', 'fake'.
    """
    if name == "fake":
        return FakeTTSProvider()
    if name == "hosted":
        from supafone_labs.tts.hosted_tts import HostedTTSProvider

        return HostedTTSProvider(**kwargs)
    if name == "deepgram":
        from supafone_labs.tts.deepgram_tts import DeepgramTTSProvider

        return DeepgramTTSProvider(**kwargs)
    if name == "cartesia":
        from supafone_labs.tts.cartesia_tts import CartesiaTTSProvider

        return CartesiaTTSProvider(**kwargs)
    if name == "elevenlabs":
        from supafone_labs.tts.elevenlabs_tts import ElevenLabsTTSProvider

        return ElevenLabsTTSProvider(**kwargs)
    if name == "inworld":
        from supafone_labs.tts.inworld_tts import InworldTTSProvider

        return InworldTTSProvider(**kwargs)
    if name in (None, "supafone_labs", "auto"):
        from supafone_labs.tts.supafone_labs_tts import SupafoneLabsTTS

        return SupafoneLabsTTS(**kwargs)
    raise ValueError(f"Unknown TTS provider: {name!r}")


def get_default_tts_provider() -> TTSProvider:
    """Auto-resolved default: hosted (pro) -> BYO keys -> offline fake."""
    return get_tts_provider()


def available_tts_backends() -> list[str]:
    """Which real backends are usable right now, by key presence (fake always works)."""
    names: list[str] = []
    if license_key():
        names.append("hosted")
    if os.getenv("DEEPGRAM_API_KEY"):
        names.append("deepgram")
    if os.getenv("CARTESIA_API_KEY"):
        names.append("cartesia")
    if os.getenv("ELEVENLABS_API_KEY"):
        names.append("elevenlabs")
    if os.getenv("INWORLD_API_KEY"):
        names.append("inworld")
    names.append("fake")
    return names
