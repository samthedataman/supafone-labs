"""Supervisor runtime settings. Environment driven; never stores credentials."""
from __future__ import annotations

import os

from pydantic import AliasChoices, BaseModel, Field

DEFAULT_SUPERVISOR_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_CRITIC_MODEL = "claude-sonnet-4-6"

# Bootstrap/offline FALLBACK only — the live source of truth is
# supafone_labs.models.discover_supervisor_models(), which queries each vendor's
# /v1/models endpoint so new releases appear (and deprecations vanish) without
# a package update. Nothing validates against this table at call time: any
# model your key can reach works via SupafoneLabs(supervisor_model=...).
SUPERVISOR_MODELS: dict[str, list[str]] = {
    "anthropic": ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-8"],
    "openai": ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"],
    "xai": ["grok-4-fast"],
    # hosted aliases resolve server-side so they never go stale in user code
    "hosted": ["supafone-supervisor", "supafone-supervisor-pro"],
}


def provider_for_model(model: str) -> str:
    """Infer which LLM provider serves a model id ('' when unknown)."""
    name = str(model or "").lower()
    for provider, models in SUPERVISOR_MODELS.items():
        if model in models:
            return provider
    if name.startswith("claude"):
        return "anthropic"
    if name.startswith(("gpt", "o1", "o3", "o4")):
        return "openai"
    if name.startswith("grok"):
        return "xai"
    if name.startswith(("supafone-labs", "supafone-supervisor")):
        return "hosted"
    return ""


class Settings(BaseModel):
    """SupafoneLabs configuration. API keys are read from the environment, not stored here."""

    supervisor_model: str = Field(
        default=os.getenv(
            "SUPAFONE_SUPERVISOR_MODEL",
            os.getenv("SUPAFONE_LABS_ORACLE_MODEL", DEFAULT_SUPERVISOR_MODEL),
        ),
        validation_alias=AliasChoices("supervisor_model", "oracle_model"),
    )
    critic_model: str = os.getenv("SUPAFONE_LABS_CRITIC_MODEL", DEFAULT_CRITIC_MODEL)
    confidence_threshold: float = float(os.getenv("SUPAFONE_LABS_CONFIDENCE_THRESHOLD", "0.5"))
    supervisor_timeout_seconds: float = Field(
        default=float(
            os.getenv(
                "SUPAFONE_SUPERVISOR_TIMEOUT",
                os.getenv("SUPAFONE_LABS_ORACLE_TIMEOUT", "8.0"),
            )
        ),
        validation_alias=AliasChoices("supervisor_timeout_seconds", "oracle_timeout_seconds"),
    )

    @property
    def oracle_model(self) -> str:
        """Deprecated compatibility alias for ``supervisor_model``."""
        return self.supervisor_model

    @property
    def oracle_timeout_seconds(self) -> float:
        """Deprecated compatibility alias for ``supervisor_timeout_seconds``."""
        return self.supervisor_timeout_seconds


def get_settings() -> Settings:
    """Return a fresh Settings instance."""
    return Settings()


# Backward-compatible imports. New code should use the supervisor names above.
DEFAULT_ORACLE_MODEL = DEFAULT_SUPERVISOR_MODEL
ORACLE_MODELS = SUPERVISOR_MODELS
