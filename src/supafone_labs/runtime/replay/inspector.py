from __future__ import annotations

from supafone_labs.runtime.core.state import RuntimeState


class ReplayInspector:
    def summarize(self, state: RuntimeState) -> dict[str, object]:
        return {
            "provider": state.provider,
            "workflow_id": state.workflow_id,
            "current_stage": state.current_stage,
            "transcript_turns": len(state.transcript),
            "tool_events": len(state.tool_history),
            "booking_verified": state.truth_state.booking_verified,
            "delivery_verified": state.truth_state.delivery_verified,
            "sms_consent": state.consent_state.sms_status,
            "recording_available": state.recording_state.recording_available,
        }
