"""SupervisorWorkflow drains ready directives without making an LLM call."""
from __future__ import annotations

from typing import Optional

from supafone_labs.supervisor.session import SupervisorSession
from supafone_labs.runtime.core.decision import RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent
from supafone_labs.runtime.core.state import RuntimeState
from supafone_labs.types import directive_to_decision


class SupervisorWorkflow:
    """Plug live supervision into the runtime while inference stays off path."""

    name = "supafone_supervisor"

    def __init__(
        self,
        session: SupervisorSession,
        threshold: Optional[float] = None,
        name: Optional[str] = None,
    ) -> None:
        self.session = session
        self.threshold = threshold if threshold is not None else session.config.confidence_threshold
        if name:
            self.name = name

    def on_event(self, state: RuntimeState, event: CanonicalEvent) -> list[RuntimeDecision]:
        directive = self.session.drain(state.session_id)
        if directive is None:
            return []
        decision = directive_to_decision(directive, self.threshold)
        return [decision] if decision else []
