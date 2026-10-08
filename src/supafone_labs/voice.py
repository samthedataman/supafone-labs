"""Common hosted voice operations. Runtime adapters never own vendor secrets."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from supafone_labs.client import Supafone


class SupafoneVoice:
    """One Agent Factory contract for hybrid, native S2S and composed pipelines."""

    def __init__(self, client: Supafone) -> None:
        self._client = client

    def _route_payload(self, *, creating: bool = False) -> dict[str, Any]:
        raise NotImplementedError("Choose SupafoneS2S or SupafonePipeline")

    def create(self, config: Mapping[str, Any] | None = None, **kwargs: Any) -> Any:
        data = {**(config or {}), **kwargs}
        if "realtime" in data or "pipeline" in data:
            raise ValueError("Set the route on the voice/S2S adapter, not create(realtime=... or pipeline=...)")
        return self._client.labs.agents.create({**data, **self._route_payload(creating=True)})

    def apply(self, agent_key: str, *, agency_id: str | None = None) -> Any:
        """Select the saved runtime for subsequent calls; preserve workflow and history."""
        self._check_agent_key(agent_key)
        return self._client.labs.agents.update(
            agent_key, self._route_payload(), agency_id=agency_id
        )

    def test_call(self, agent_key: str, *, agency_id: str | None = None) -> Any:
        """Preview the saved agent. This never applies a route implicitly."""
        self._check_agent_key(agent_key)
        return self._client.labs.agents.test_call(agent_key, agency_id=agency_id)

    testCall = test_call

    @staticmethod
    def _check_agent_key(agent_key: str) -> None:
        if not isinstance(agent_key, str) or not agent_key.strip():
            raise ValueError("agent_key is required")
