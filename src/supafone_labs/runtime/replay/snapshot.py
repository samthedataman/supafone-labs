from __future__ import annotations

from pydantic import BaseModel

from supafone_labs.runtime.core.state import RuntimeState


class StateSnapshot(BaseModel):
    event_count: int
    state: RuntimeState

    @classmethod
    def from_state(cls, state: RuntimeState, *, event_count: int) -> "StateSnapshot":
        return cls(event_count=event_count, state=state.model_copy(deep=True))
