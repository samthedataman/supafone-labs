"""OracleWorkflow — a runtime WorkflowDefinition that drains oracle directives (no LLM call)."""
from __future__ import annotations

from typing import Optional

from supafone_labs.oracle.session import OracleSession
from supafone_labs.runtime.core.decision import RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent
from supafone_labs.runtime.core.state import RuntimeState
from supafone_labs.types import directive_to_decision


class OracleWorkflow:
    """Plugs the oracle into the runtime. `on_event` is SYNC and only drains the buffer —
    the LLM work happens off the hot path in OracleSession.observe."""

    name = "supafone_labs_oracle"

    def __init__(
        self,
        session: OracleSession,
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
