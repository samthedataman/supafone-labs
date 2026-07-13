"""supafone_labs.tts — Supafone Labs' own text-to-speech layer.

``SupafoneLabsTTS`` is the default voice: managed Cartesia on the pro tier,
BYO Cartesia on the free tier, and an offline fake with no key. Other engines
remain available only when selected explicitly.
"""
from supafone_labs.tts.base import FakeTTSProvider, TTSProvider
from supafone_labs.tts.cartesia_tts import CartesiaTTSProvider
from supafone_labs.tts.deepgram_tts import DeepgramTTSProvider
from supafone_labs.tts.elevenlabs_tts import ElevenLabsTTSProvider
from supafone_labs.tts.hosted_tts import HostedTTSProvider
from supafone_labs.tts.inworld_tts import InworldTTSProvider
from supafone_labs.tts.registry import (
    available_tts_backends,
    get_default_tts_provider,
    get_tts_provider,
)
from supafone_labs.tts.supafone_labs_tts import SupafoneLabsTTS

__all__ = [
    "TTSProvider",
    "FakeTTSProvider",
    "SupafoneLabsTTS",
    "HostedTTSProvider",
    "DeepgramTTSProvider",
    "CartesiaTTSProvider",
    "ElevenLabsTTSProvider",
    "InworldTTSProvider",
    "get_tts_provider",
    "get_default_tts_provider",
    "available_tts_backends",
]
