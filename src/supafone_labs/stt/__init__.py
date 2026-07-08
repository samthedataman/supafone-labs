"""supafone_labs.stt — live multilingual transcription (Deepgram nova-3 multi).

The tap for stacks that stream audio instead of transcripts, and the language
authority for multilingual calls on providers whose transcripts carry no
language tag. ``recommended_setup(provider)`` tells you which combination
you're in.
"""
from supafone_labs.stt.deepgram_live import DeepgramLiveSTT, MultilingualCallTap
from supafone_labs.stt.language import (
    NOVA3_MULTI_LANGUAGES,
    PROVIDER_PROFILES,
    STTMode,
    TapRecommendation,
    choose_language_mode,
    needs_deepgram_tap,
    recommended_setup,
)

__all__ = [
    "DeepgramLiveSTT",
    "MultilingualCallTap",
    "STTMode",
    "TapRecommendation",
    "choose_language_mode",
    "needs_deepgram_tap",
    "recommended_setup",
    "NOVA3_MULTI_LANGUAGES",
    "PROVIDER_PROFILES",
]
