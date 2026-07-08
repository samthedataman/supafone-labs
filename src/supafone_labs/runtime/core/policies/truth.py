from __future__ import annotations

from typing import TYPE_CHECKING

from supafone_labs.runtime.core.decision import RuntimeDecision

if TYPE_CHECKING:
    from supafone_labs.runtime.core.state import RuntimeState


class TruthPolicy:
    def reconcile_end_call_summary(
        self,
        state: RuntimeState,
        *,
        summary: str,
    ) -> RuntimeDecision | None:
        lowered = summary.lower()
        issues: list[str] = []

        if any(term in lowered for term in ("booked", "scheduled", "confirmed")):
            if not state.truth_state.booking_verified:
                issues.append("Summary claims a booking that was never verified.")

        if any(term in lowered for term in ("texted", "sms", "sent by text", "emailed", "sent")):
            if not state.truth_state.delivery_verified:
                issues.append("Summary claims delivery that was never verified.")

        if not issues:
            return None
        return RuntimeDecision.reconcile_call_summary(summary=summary, issues=issues)
