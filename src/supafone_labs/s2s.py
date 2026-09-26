"""One hosted agent interface for Supafone's speech-to-speech providers.

These adapters configure Supafone's hosted runtime. Provider credentials and
audio connections stay on the server; they are not local vendor SDK clients.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Mapping

if TYPE_CHECKING:
    from supafone_labs.client import Supafone

S2SProviderName = Literal["ultravox", "openai", "google", "xai", "smallest"]
_PROVIDERS = frozenset({"ultravox", "openai", "google", "xai", "smallest"})


class SupafoneS2S:
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

    def create(self, config: Mapping[str, Any] | None = None, **kwargs: Any) -> Any:
        """Create through the normal agent factory using this provider."""
        data = {**(config or {}), **kwargs}
        if "realtime" in data:
            raise ValueError(
                "Set provider/model/voice on the S2S adapter, not create(realtime=...)"
            )
        if self.realtime is not None:
            data["realtime"] = self.realtime
        return self._client.labs.agents.create(data)

    def apply(self, agent_key: str, *, agency_id: str | None = None) -> Any:
        """Change only the saved S2S selection, keeping this agent and its number."""
        self._check_agent_key(agent_key)
        return self._client.labs.agents.update(
            agent_key, realtime=self.realtime, agency_id=agency_id
        )

    def test_call(self, agent_key: str, *, agency_id: str | None = None) -> Any:
        """Preview the saved agent; call apply first when switching providers."""
        self._check_agent_key(agent_key)
        return self._client.labs.agents.test_call(agent_key, agency_id=agency_id)

    testCall = test_call

    @staticmethod
    def _check_agent_key(agent_key: str) -> None:
        if not isinstance(agent_key, str) or not agent_key.strip():
            raise ValueError("agent_key is required")


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
