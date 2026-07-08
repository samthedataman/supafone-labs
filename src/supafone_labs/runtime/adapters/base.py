from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol

from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent, EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState


class VoiceProviderAdapter(Protocol):
    provider_name: str

    def capabilities(self) -> ProviderCapabilities:
        ...

    async def create_session(self, request: dict[str, Any]) -> dict[str, Any]:
        ...

    async def parse_event(self, raw_event: dict[str, Any]) -> list[CanonicalEvent]:
        ...

    async def compile(
        self,
        decision: RuntimeDecision,
        state: RuntimeState,
    ) -> list[ProviderAction]:
        ...

    async def execute(self, actions: list[ProviderAction], state: RuntimeState) -> list[CanonicalEvent]:
        ...

    async def fetch_artifacts(self, session_id: str) -> list[CanonicalEvent]:
        ...


class BaseAdapter(ABC):
    provider_name: str

    def _session_id(self, raw_event: dict[str, Any]) -> str:
        return str(raw_event.get("session_id") or raw_event.get("call_id") or "session")

    def _provider_session_id(self, raw_event: dict[str, Any]) -> str:
        return str(raw_event.get("provider_session_id") or raw_event.get("conversation_id") or "")

    async def create_session(self, request: dict[str, Any]) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "session_id": request.get("session_id", "session"),
            "created": True,
        }

    async def execute(self, actions: list[ProviderAction], state: RuntimeState) -> list[CanonicalEvent]:
        events: list[CanonicalEvent] = []
        for action in actions:
            events.append(
                make_event(
                    EventTypes.PROVIDER_ACTION_EXECUTED,
                    session_id=state.session_id,
                    provider=self.provider_name,
                    provider_session_id=state.provider_session_id,
                    actor="provider",
                    data={
                        "kind": action.kind,
                        "payload": action.payload,
                    },
                )
            )
        return events

    async def fetch_artifacts(self, session_id: str) -> list[CanonicalEvent]:
        return []

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        raise NotImplementedError

    @abstractmethod
    async def parse_event(self, raw_event: dict[str, Any]) -> list[CanonicalEvent]:
        raise NotImplementedError

    @abstractmethod
    async def compile(
        self,
        decision: RuntimeDecision,
        state: RuntimeState,
    ) -> list[ProviderAction]:
        raise NotImplementedError
