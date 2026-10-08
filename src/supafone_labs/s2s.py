"""One hosted agent interface for Supafone's speech-to-speech providers.

These adapters configure Supafone's hosted runtime. Provider credentials and
audio connections stay on the server; they are not local vendor SDK clients.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from supafone_labs.client import Supafone

from supafone_labs.voice import SupafoneVoice

S2SProviderName = Literal["ultravox", "openai", "google", "xai", "smallest"]
_PROVIDERS = frozenset({"ultravox", "openai", "google", "xai", "smallest"})


class SupafoneS2S(SupafoneVoice):
    """Shared parent for hosted S2S agent creation, selection, and preview.

    ``apply`` changes the saved model for subsequent calls. ``test_call`` uses
    the agent's saved selection and never changes it implicitly. Model/voice
    validation and credential readiness come from the server's live catalog.
    """

    def __init__(
        self,
        client: Supafone,
        *,
        provider: S2SProviderName = "ultravox",
        model: str | None = None,
        voice: str | None = None,
    ) -> None:
        if not isinstance(provider, str) or provider not in _PROVIDERS:
            raise ValueError("Unsupported Supafone S2S provider")
        if provider == "ultravox" and (model is not None or voice is not None):
            raise ValueError("Configure Ultravox voices through the agent's voice settings")
        selection: dict[str, str] = {"provider": provider}
        for field, value in (("model", model), ("voice", voice)):
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{field} must be a non-empty string")
                selection[field] = value.strip()
        self._client = client
        self._provider = provider
        self._selection = selection if provider != "ultravox" else None

    @property
    def provider(self) -> S2SProviderName:
        return self._provider

    @property
    def realtime(self) -> dict[str, str] | None:
        """A fresh wire selection; None explicitly restores default Ultravox."""
        return dict(self._selection) if self._selection is not None else None

    def _route_payload(self, *, creating: bool = False) -> dict[str, Any]:
        # Keep the existing Ultravox omission/null semantics. The server clears
        # pipeline when an update explicitly supplies realtime, including null.
        if creating and self.realtime is None:
            return {}
        return {"realtime": self.realtime}


class UltravoxS2S(SupafoneS2S):
    """The existing hosted Ultravox runtime, including its original stage flow."""

    def __init__(self, client: Supafone) -> None:
        super().__init__(client, provider="ultravox")


class OpenAIS2S(SupafoneS2S):
    """Supafone's OpenAI Realtime and GPT Live adapters."""

    def __init__(
        self, client: Supafone, *, model: str | None = None, voice: str | None = None
    ) -> None:
        super().__init__(client, provider="openai", model=model, voice=voice)


class GeminiS2S(SupafoneS2S):
    """Supafone's Google Gemini Live adapter."""

    def __init__(
        self, client: Supafone, *, model: str | None = None, voice: str | None = None
    ) -> None:
        super().__init__(client, provider="google", model=model, voice=voice)


class GrokS2S(SupafoneS2S):
    """Supafone's xAI Grok Voice adapter."""

    def __init__(
        self, client: Supafone, *, model: str | None = None, voice: str | None = None
    ) -> None:
        super().__init__(client, provider="xai", model=model, voice=voice)


class HydraS2S(SupafoneS2S):
    """Supafone's Smallest AI Hydra adapter (audio without transcript events)."""

    def __init__(
        self, client: Supafone, *, model: str | None = None, voice: str | None = None
    ) -> None:
        super().__init__(client, provider="smallest", model=model, voice=voice)
