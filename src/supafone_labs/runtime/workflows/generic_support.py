from __future__ import annotations

from supafone_labs.runtime.core.decision import RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent, EventTypes
from supafone_labs.runtime.core.state import RuntimeState


class GenericSupportWorkflow:
    name = "generic_support"

    def on_event(self, state: RuntimeState, event: CanonicalEvent) -> list[RuntimeDecision]:
        decisions: list[RuntimeDecision] = []
        if event.type == EventTypes.TOOL_RESULT:
            tool_name = str(event.data.get("tool_name") or event.data.get("name") or "")
            status = str(event.data.get("status") or "").lower()
            if tool_name == "book_appointment" and status == "booked" and state.current_stage != "confirmation":
                decisions.append(RuntimeDecision.force_stage_transition("confirmation"))
        if event.type == EventTypes.CALLER_TRANSCRIPT_FINAL:
            if "schedule" in event.text.lower() and state.current_stage == "intake":
                decisions.append(RuntimeDecision.force_stage_transition("booking"))
        return decisions
