"""Language-mode resolution + the provider/transcript combination matrix.

Two hard problems live here:

1. **Which Deepgram mode to run.** nova-3's ``language=multi`` does live
   code-switching across ten languages — the right default for calls where you
   don't know what the caller will speak. But if the operator pins languages
   outside that set, multi would silently mis-transcribe; the resolver drops to
   the best mono model/language instead.

2. **Where transcripts should come from per provider.** Some stacks stream
   their own transcripts (tap those, no STT bill), some stream audio only
   (run the Deepgram tap), and none of the agent platforms tag language
   reliably — so the tap is also the *language authority* when multilingual
   calls matter. ``recommended_setup`` encodes the matrix so integrators don't
   re-derive it, and so we never double-ingest the same speech from two
   sources.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from supafone_labs.types import normalize_language_code

# nova-3 `language=multi` code-switching set (Deepgram docs, mid-2026).
NOVA3_MULTI_LANGUAGES = frozenset({"en", "es", "fr", "de", "hi", "ru", "pt", "ja", "it", "nl"})

# Broad mono-language coverage lives on nova-2; nova-3 mono covers the multi set.
DEFAULT_MULTI_MODEL = "nova-3"
DEFAULT_MONO_FALLBACK_MODEL = "nova-2"


@dataclass
class STTMode:
    model: str
    language: str
    code_switching: bool
    notes: str = ""


def choose_language_mode(preferred: list[str] | None = None) -> STTMode:
    """Resolve the Deepgram model+language for a set of expected caller languages.

    - No expectation (or everything in the multi set) -> nova-3 ``multi``:
      live code-switching, per-result ``languages`` tags.
    - One language outside the multi set -> mono mode on that language.
    - Several languages that multi can't cover together -> mono on the FIRST
      preference, with an explicit note (Deepgram has no arbitrary-set
      code-switching; pretending otherwise would corrupt transcripts).
    """
    codes = [normalize_language_code(lang) for lang in (preferred or [])]
    codes = list(dict.fromkeys(c for c in codes if c and c != "unknown"))
    if len(codes) == 1:
        # One pinned language is an explicit operator choice: mono beats multi
        # on accuracy, even for languages the multi set covers.
        code = codes[0]
        model = DEFAULT_MULTI_MODEL if code in NOVA3_MULTI_LANGUAGES else DEFAULT_MONO_FALLBACK_MODEL
        return STTMode(
            model=model,
            language=code,
            code_switching=False,
            notes=f"pinned mono transcription in '{code}'.",
        )
    if not codes or all(c in NOVA3_MULTI_LANGUAGES for c in codes):
        return STTMode(
            model=DEFAULT_MULTI_MODEL,
            language="multi",
            code_switching=True,
            notes="nova-3 multi: live code-switching; results carry per-utterance language tags.",
        )
    primary = codes[0]
    model = DEFAULT_MULTI_MODEL if primary in NOVA3_MULTI_LANGUAGES else DEFAULT_MONO_FALLBACK_MODEL
    return STTMode(
        model=model,
        language=primary,
        code_switching=False,
        notes=(
            f"languages {codes} exceed nova-3 multi coverage; pinned to '{primary}'. "
            "Split tracks per expected language if callers genuinely mix these."
        ),
    )


# --- the combination matrix -------------------------------------------------------

@dataclass
class ProviderTranscriptProfile:
    streams_transcripts: bool          # does the provider push live transcript events?
    language_tagged: bool              # ...with a per-utterance language tag?
    audio_accessible: bool             # can you fork/tap the raw audio?
    notes: str = ""


# What each supported stack actually gives you (doc/live-verified alongside the
# adapters). "language_tagged" is the rare one — almost nobody tags language.
PROVIDER_PROFILES: dict[str, ProviderTranscriptProfile] = {
    "ultravox": ProviderTranscriptProfile(True, False, True, "WS transcripts; fork Twilio media for the tap."),
    "vapi": ProviderTranscriptProfile(True, False, False, "webhook transcripts (transcriptType partial/final)."),
    "bland": ProviderTranscriptProfile(True, False, True, "webhook_events speech lines; audio via listen WS."),
    "retell": ProviderTranscriptProfile(True, False, False, "custom-LLM WS transcript array."),
    "gpt_realtime": ProviderTranscriptProfile(True, False, True, "input_audio_transcription events; audio via WS."),
    "grok": ProviderTranscriptProfile(True, False, True, "cumulative input transcription; audio via WS."),
    "elevenlabs": ProviderTranscriptProfile(True, False, True, "user_transcript / agent_response events."),
    "deepgram": ProviderTranscriptProfile(True, True, True, "Voice Agent ConversationText; STT Results tag languages."),
    "pipecat": ProviderTranscriptProfile(True, False, True, "TranscriptionFrame has a language field when the STT sets it."),
    "livekit": ProviderTranscriptProfile(True, False, True, "user_input_transcribed has a language field when set."),
    "cartesia": ProviderTranscriptProfile(True, False, True, "Ink transcript messages (live-verified language tag)."),
    "inworld": ProviderTranscriptProfile(True, False, False, "character/TTS events."),
    "twilio": ProviderTranscriptProfile(False, False, True, "raw media stream: audio only — the tap is mandatory."),
    "raw_audio": ProviderTranscriptProfile(False, False, True, "any bare audio source."),
}


@dataclass
class TapRecommendation:
    run_deepgram_tap: bool
    transcript_source: str          # "provider" | "deepgram_tap"
    language_source: str            # "provider" | "deepgram_tap" | "oracle_heuristics"
    mode: STTMode = field(default_factory=lambda: choose_language_mode(None))
    notes: str = ""


def needs_deepgram_tap(provider: str, *, multilingual: bool = False) -> bool:
    """True when the stack can't deliver what the oracle needs without our own STT."""
    profile = PROVIDER_PROFILES.get(str(provider or "").lower())
    if profile is None or not profile.streams_transcripts:
        return True
    return multilingual and not profile.language_tagged and profile.audio_accessible


def recommended_setup(
    provider: str,
    *,
    multilingual: bool = False,
    preferred_languages: list[str] | None = None,
) -> TapRecommendation:
    """The one rule that prevents every bad combination: exactly ONE transcript
    source feeds the oracle per call.

    - Provider streams transcripts + monolingual -> use provider transcripts;
      the oracle's language heuristics cover the rare stray sentence.
    - Provider streams transcripts + multilingual matters -> run the tap as the
      transcript AND language authority (provider transcripts get ignored, not
      merged — merging double-ingests every utterance).
    - Audio-only stacks (Twilio forks, raw S2S audio) -> the tap is the only
      option.
    """
    name = str(provider or "").lower()
    profile = PROVIDER_PROFILES.get(name)
    mode = choose_language_mode(preferred_languages)

    if profile is None or not profile.streams_transcripts:
        return TapRecommendation(
            run_deepgram_tap=True,
            transcript_source="deepgram_tap",
            language_source="deepgram_tap" if mode.code_switching else "oracle_heuristics",
            mode=mode,
            notes=f"'{name or 'unknown'}' provides no transcript stream — the tap is mandatory.",
        )
    if multilingual and not profile.language_tagged:
        if profile.audio_accessible:
            return TapRecommendation(
                run_deepgram_tap=True,
                transcript_source="deepgram_tap",
                language_source="deepgram_tap",
                mode=mode,
                notes=(
                    f"'{name}' transcripts are not language-tagged; the tap becomes the single "
                    "transcript source (do NOT also feed provider transcripts — double ingestion)."
                ),
            )
        return TapRecommendation(
            run_deepgram_tap=False,
            transcript_source="provider",
            language_source="oracle_heuristics",
            mode=mode,
            notes=(
                f"'{name}' exposes no raw audio to tap; provider transcripts + the oracle's "
                "language heuristics are the best available."
            ),
        )
    return TapRecommendation(
        run_deepgram_tap=False,
        transcript_source="provider",
        language_source="provider" if profile.language_tagged else "oracle_heuristics",
        mode=mode,
        notes=f"'{name}' transcripts feed the oracle directly; no STT double-spend.",
    )
