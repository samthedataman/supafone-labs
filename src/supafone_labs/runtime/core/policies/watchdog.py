from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from supafone_labs.runtime.core.decision import RuntimeDecision

if TYPE_CHECKING:
    from supafone_labs.runtime.core.state import RuntimeState

BRIDGE_PHRASES = (
    "let me check",
    "i'll be right back",
    "i will be right back",
    "one moment while i check",
    "please hold while i process",
    "let me send that now",
)


def is_bridge_phrase(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in BRIDGE_PHRASES)


class DeadAirWatchdogPolicy:
    def __init__(self, delay_seconds: float = 4.0):
        self.delay_seconds = delay_seconds

    def evaluate(
        self,
        state: RuntimeState,
        *,
        now: datetime | None = None,
    ) -> RuntimeDecision | None:
        if not state.watchdog_state.bridge_armed:
            return None
        if state.watchdog_state.bridge_armed_at is None:
            return None

        current = now or datetime.now(timezone.utc)
        delay = (current - state.watchdog_state.bridge_armed_at).total_seconds()
        if delay < self.delay_seconds:
            return None

        if state.current_stage == "intake":
            next_step = (
                "If the caller is ready to move forward, transition to the next workflow stage "
                "and continue immediately."
            )
        elif state.current_stage == "booking":
            next_step = "Continue with live availability or booking immediately."
        else:
            next_step = "Continue with the next workflow action immediately."

        return RuntimeDecision.inject_hidden_instruction(
            "You already told the caller you were checking. Continue immediately without "
            f"waiting for more input. {next_step} Do not repeat the same hold phrase."
        )
