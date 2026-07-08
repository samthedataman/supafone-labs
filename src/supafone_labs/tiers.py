"""Free vs paid tiering.

SupafoneLabs is MIT-licensed and fully functional on the **free** tier with your
own keys (BYO Anthropic/OpenAI for the oracle, BYO Deepgram/Cartesia/ElevenLabs
for TTS) — or with no keys at all via the offline fake providers.

Setting ``SUPAFONE_LABS_API_KEY`` unlocks the **pro** tier: the oracle and TTS run
against Supafone Labs' hosted endpoints on Supafone Labs' own model keys, so users
never manage LLM/voice credentials. Everything else is identical — tiering
gates *who pays for inference*, never correctness or safety.
"""
from __future__ import annotations

import os
from enum import Enum


class Tier(str, Enum):
    FREE = "free"
    PRO = "pro"


# What each tier can use. Deliberately small and honest: the free tier is not
# crippled — pro only adds Supafone Labs-managed inference.
FEATURES: dict[Tier, frozenset[str]] = {
    Tier.FREE: frozenset({"byo_oracle", "byo_tts", "offline_fake", "all_adapters"}),
    Tier.PRO: frozenset(
        {"byo_oracle", "byo_tts", "offline_fake", "all_adapters", "hosted_oracle", "hosted_tts"}
    ),
}


class TierError(RuntimeError):
    """Raised when a pro-only feature is used without a SUPAFONE_LABS_API_KEY."""


def license_key() -> str:
    return str(os.getenv("SUPAFONE_LABS_API_KEY") or "").strip()


def current_tier() -> Tier:
    """PRO when a Supafone Labs license key is present, else FREE."""
    return Tier.PRO if license_key() else Tier.FREE


def has_feature(name: str, tier: Tier | None = None) -> bool:
    return name in FEATURES[tier or current_tier()]


def require_feature(name: str) -> None:
    if not has_feature(name):
        raise TierError(
            f"'{name}' requires the Supafone Labs pro tier. Set SUPAFONE_LABS_API_KEY, "
            "or use your own provider keys on the free tier."
        )
