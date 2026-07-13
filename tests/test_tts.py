"""supafone_labs.tts — Supafone Labs' own TTS: tier-aware selection, degrade chain,
and real playable audio from the offline fake."""
from __future__ import annotations

import io
import wave

import pytest

from supafone_labs.tiers import TierError
from supafone_labs.tts import (
    CartesiaTTSProvider,
    DeepgramTTSProvider,
    ElevenLabsTTSProvider,
    FakeTTSProvider,
    HostedTTSProvider,
    InworldTTSProvider,
    SupafoneLabsTTS,
    available_tts_backends,
    get_tts_provider,
)
from supafone_labs.tts.cartesia_tts import CARTESIA_VERSION, DEFAULT_MODEL, DEFAULT_VOICE
from supafone_labs.types import Directive

ALL_KEYS = (
    "SUPAFONE_LABS_API_KEY",
    "DEEPGRAM_API_KEY",
    "CARTESIA_API_KEY",
    "ELEVENLABS_API_KEY",
    "INWORLD_API_KEY",
)


@pytest.fixture
def clean_env(monkeypatch):
    for key in ALL_KEYS:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


class _MockResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self) -> None:
        return None


class _MockClient:
    def __init__(self, content: bytes = b"AUDIO"):
        self.content = content
        self.calls: list[dict] = []

    async def post(self, url, headers=None, json=None, params=None):
        self.calls.append({"url": url, "headers": headers, "json": json, "params": params})
        return _MockResponse(self.content)

    async def aclose(self) -> None:
        return None


class _BoomBackend:
    provider_name = "boom"

    async def synthesize(self, text, *, voice=None, **kwargs):
        raise RuntimeError("backend down")


# --- offline fake ------------------------------------------------------------

async def test_fake_tts_returns_valid_playable_wav():
    audio = await FakeTTSProvider().synthesize("hello from the second mind")
    with wave.open(io.BytesIO(audio), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getnframes() > 0


async def test_fake_tts_duration_tracks_text_length():
    short = await FakeTTSProvider().synthesize("hi")
    long = await FakeTTSProvider().synthesize("this is a much longer sentence " * 5)
    assert len(long) > len(short)


# --- registry / tier selection ----------------------------------------------

def test_registry_names(clean_env):
    assert isinstance(get_tts_provider("fake"), FakeTTSProvider)
    assert isinstance(get_tts_provider("hosted"), HostedTTSProvider)
    assert isinstance(get_tts_provider("deepgram"), DeepgramTTSProvider)
    assert isinstance(get_tts_provider("cartesia"), CartesiaTTSProvider)
    assert isinstance(get_tts_provider("elevenlabs"), ElevenLabsTTSProvider)
    assert isinstance(get_tts_provider("inworld"), InworldTTSProvider)
    assert isinstance(get_tts_provider(), SupafoneLabsTTS)
    with pytest.raises(ValueError):
        get_tts_provider("nope")


def test_available_backends_by_keys(clean_env):
    assert available_tts_backends() == ["fake"]
    clean_env.setenv("DEEPGRAM_API_KEY", "dg")
    assert available_tts_backends() == ["deepgram", "fake"]
    clean_env.setenv("SUPAFONE_LABS_API_KEY", "sm")
    assert available_tts_backends()[0] == "hosted"


def test_supafone_labs_tts_free_tier_uses_cartesia_not_other_byo_keys(clean_env):
    clean_env.setenv("DEEPGRAM_API_KEY", "dg")
    clean_env.setenv("ELEVENLABS_API_KEY", "el")
    clean_env.setenv("CARTESIA_API_KEY", "ca")
    tts = SupafoneLabsTTS()
    assert isinstance(tts.active_backend, CartesiaTTSProvider)


def test_supafone_labs_tts_does_not_auto_select_elevenlabs(clean_env):
    clean_env.setenv("ELEVENLABS_API_KEY", "el")
    assert isinstance(SupafoneLabsTTS().active_backend, FakeTTSProvider)


def test_supafone_labs_tts_pro_tier_prefers_hosted(clean_env):
    clean_env.setenv("SUPAFONE_LABS_API_KEY", "sl_live_123")
    clean_env.setenv("DEEPGRAM_API_KEY", "dg")
    tts = SupafoneLabsTTS()
    assert isinstance(tts.active_backend, HostedTTSProvider)


def test_supafone_labs_tts_no_keys_is_offline_fake(clean_env):
    tts = SupafoneLabsTTS()
    assert isinstance(tts.active_backend, FakeTTSProvider)


# --- degrade chain ------------------------------------------------------------

async def test_chain_degrades_to_fake_when_backend_fails(clean_env):
    tts = SupafoneLabsTTS(backends=[_BoomBackend(), FakeTTSProvider()])
    audio = await tts.synthesize("still speaks")
    with wave.open(io.BytesIO(audio), "rb") as wav:
        assert wav.getnframes() > 0


async def test_speak_directive_voices_composed_text(clean_env):
    tts = SupafoneLabsTTS(backends=[FakeTTSProvider()])
    directive = Directive(empathy_directive="Slow down.", confidence=0.9)
    audio = await tts.speak_directive(directive)
    assert isinstance(audio, bytes) and audio


# --- real backends (mocked transport) -----------------------------------------

async def test_deepgram_tts_request_shape(clean_env):
    client = _MockClient(b"WAVBYTES")
    provider = DeepgramTTSProvider(api_key="dg_key", client=client)
    audio = await provider.synthesize("hello", voice="aura-2-thalia-en")
    assert audio == b"WAVBYTES"
    call = client.calls[0]
    assert call["url"] == "https://api.deepgram.com/v1/speak"
    assert call["params"]["model"] == "aura-2-thalia-en"
    assert call["headers"]["Authorization"] == "Token dg_key"
    assert call["json"] == {"text": "hello"}


async def test_cartesia_tts_request_shape(clean_env):
    client = _MockClient(b"WAV")
    provider = CartesiaTTSProvider(api_key="ca_key", voice=DEFAULT_VOICE, client=client)
    await provider.synthesize("hola")
    call = client.calls[0]
    assert call["url"] == "https://api.cartesia.ai/tts/bytes"
    assert call["headers"]["Authorization"] == "Bearer ca_key"
    assert call["headers"]["Cartesia-Version"] == CARTESIA_VERSION
    assert call["json"]["model_id"] == DEFAULT_MODEL
    assert call["json"]["transcript"] == "hola"
    assert call["json"]["voice"] == {"id": DEFAULT_VOICE}


async def test_cartesia_never_receives_an_elevenlabs_voice_id(clean_env):
    client = _MockClient(b"WAV")
    provider = CartesiaTTSProvider(api_key="ca_key", client=client)
    await provider.synthesize("hello", voice="21m00Tcm4TlvDq8ikWAM")
    assert client.calls[0]["json"]["voice"] == {"id": DEFAULT_VOICE}


async def test_elevenlabs_tts_request_shape(clean_env):
    client = _MockClient(b"MP3")
    provider = ElevenLabsTTSProvider(api_key="el_key", voice="voice_1", client=client)
    await provider.synthesize("bonjour")
    call = client.calls[0]
    assert call["url"].endswith("/text-to-speech/voice_1")
    assert call["headers"]["xi-api-key"] == "el_key"
    assert call["json"]["text"] == "bonjour"


async def test_inworld_tts_request_shape_and_b64_decode(clean_env):
    import base64

    class _JsonResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class _JsonClient(_MockClient):
        async def post(self, url, headers=None, json=None, params=None):
            self.calls.append({"url": url, "headers": headers, "json": json})
            return _JsonResponse({"audioContent": base64.b64encode(b"RIFFaudio").decode()})

    client = _JsonClient()
    provider = InworldTTSProvider(api_key="iw_key", voice="Ashley", client=client)
    audio = await provider.synthesize("hi")
    assert audio == b"RIFFaudio"
    call = client.calls[0]
    assert call["url"] == "https://api.inworld.ai/tts/v1/voice"
    assert call["headers"]["Authorization"] == "Basic iw_key"
    assert call["json"]["voiceId"] == "Ashley"


async def test_hosted_tts_requires_license(clean_env):
    provider = HostedTTSProvider(api_key="", client=_MockClient())
    with pytest.raises(TierError):
        await provider.synthesize("hi")


async def test_hosted_tts_request_shape(clean_env):
    client = _MockClient(b"WAV")
    provider = HostedTTSProvider(api_key="sl_live_123", client=client)
    await provider.synthesize("hi", voice="supafone-labs-calm-en")
    call = client.calls[0]
    assert call["url"].endswith("/tts")
    assert call["headers"]["Authorization"] == "Bearer sl_live_123"
    assert call["json"]["voice"] == "supafone-labs-calm-en"


# --- facade integration --------------------------------------------------------

async def test_facade_speak_uses_own_tts(clean_env):
    from supafone_labs import SupafoneLabs
    from supafone_labs.llm import FakeLLMProvider
    from supafone_labs.oracle.session import OracleSession

    brain = SupafoneLabs(
        provider="ultravox",
        oracle=OracleSession(provider=FakeLLMProvider()),
        mode="return",
        tts=SupafoneLabsTTS(backends=[FakeTTSProvider()]),
    )
    await brain.observe(
        {"type": "transcript", "speaker": "caller", "text": "I was rear-ended.", "final": True, "call_id": "c1"}
    )
    audio = await brain.speak()  # voices the buffered directive
    with wave.open(io.BytesIO(audio), "rb") as wav:
        assert wav.getnframes() > 0
