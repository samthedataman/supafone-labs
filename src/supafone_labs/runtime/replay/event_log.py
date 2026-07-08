from __future__ import annotations

from pydantic import BaseModel, Field

from supafone_labs.runtime.core.events import CanonicalEvent
from supafone_labs.runtime.core.state import RuntimeState, apply_events


class ReplaySession(BaseModel):
    events: list[CanonicalEvent] = Field(default_factory=list)

    def append(self, event: CanonicalEvent) -> None:
        self.events.append(event)

    def extend(self, events: list[CanonicalEvent]) -> None:
        self.events.extend(events)

    def replay(self, initial_state: RuntimeState) -> RuntimeState:
        return apply_events(self.events, initial_state)
