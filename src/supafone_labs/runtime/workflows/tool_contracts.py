from __future__ import annotations

from typing import Protocol

from supafone_labs.runtime.core.decision import RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent
from supafone_labs.runtime.core.state import RuntimeState


class WorkflowDefinition(Protocol):
    name: str

    def on_event(self, state: RuntimeState, event: CanonicalEvent) -> list[RuntimeDecision]:
        ...
