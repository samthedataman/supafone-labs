from __future__ import annotations

from typing import TYPE_CHECKING

from supafone_labs.runtime.core.decision import RuntimeDecision

if TYPE_CHECKING:
    from supafone_labs.runtime.core.state import RuntimeState


class ConsentPolicy:
    def evaluate_delivery_request(
        self,
        state: RuntimeState,
        *,
        channel: str,
        purpose: str,
    ) -> RuntimeDecision | None:
        normalized_channel = channel.strip().lower()
        if normalized_channel != "sms":
            return None
        if state.consent_state.sms_status == "granted":
            return None
        return RuntimeDecision.block_delivery_until_consent(
            channel=normalized_channel,
            purpose=purpose,
        )
