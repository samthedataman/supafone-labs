"""Runtime settings (env-driven). Latest Claude defaults; never holds secrets."""
from __future__ import annotations

import os

from pydantic import BaseModel

DEFAULT_ORACLE_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_CRITIC_MODEL = "claude-sonnet-4-6"

# Bootstrap/offline FALLBACK only — the live source of truth is
# supafone_labs.models.discover_oracle_models(), which queries each vendor's
# /v1/models endpoint so new releases appear (and deprecations vanish) without
# a package update. Nothing validates against this table at call time: any
# model your key can reach works via SupafoneLabs(oracle_model=...).
ORACLE_MODELS: dict[str, list[str]] = {
    "anthropic": ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-8"],
    "openai": ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"],
    "xai": ["grok-4-fast"],
    # hosted aliases resolve server-side so they never go stale in user code
    "hosted": ["supafone-labs-oracle", "supafone-labs-oracle-pro"],
}


def provider_for_model(model: str) -> str:
    """Infer which LLM provider serves a model id ('' when unknown)."""
    name = str(model or "").lower()
    for provider, models in ORACLE_MODELS.items():
        if model in models:
            return provider
    if name.startswith("claude"):
        return "anthropic"
    if name.startswith(("gpt", "o1", "o3", "o4")):
        return "openai"
    if name.startswith("grok"):
        return "xai"
    if name.startswith("supafone-labs"):
        return "hosted"
    return ""


class Settings(BaseModel):
    """SupafoneLabs configuration. API keys are read from the environment, not stored here."""

    oracle_model: str = os.getenv("SUPAFONE_LABS_ORACLE_MODEL", DEFAULT_ORACLE_MODEL)
    critic_model: str = os.getenv("SUPAFONE_LABS_CRITIC_MODEL", DEFAULT_CRITIC_MODEL)
    confidence_threshold: float = float(os.getenv("SUPAFONE_LABS_CONFIDENCE_THRESHOLD", "0.5"))
    oracle_timeout_seconds: float = float(os.getenv("SUPAFONE_LABS_ORACLE_TIMEOUT", "8.0"))


def get_settings() -> Settings:
    """Return a fresh Settings instance."""
    return Settings()
