"""Post-call analysis — deterministic outcome scoring from the runtime's ground truth.

No LLM needed: the runtime state already knows whether the booking the agent
promised was actually verified, whether the intake form actually sent, and
whether the agent's end-of-call claims were backed by tool results. That's the
reward signal the optimizer learns from — measured, not vibes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from supafone_labs.runtime.core.state import RuntimeState


@dataclass
class CallReport:
    session_id: str
    agent: str = "default"
    score: float = 1.0
    outcome: str = "clean"
    summary: str = "clean call"
    issues: list[str] = field(default_factory=list)
    nudges: int = 0
    turns: int = 0
    language: str = ""


def score_call(
    state: RuntimeState, *, nudges: int = 0, agent: str = "default"
) -> CallReport:
    """Grade one finished call against what the runtime verified actually happened."""
    issues: list[str] = []
    score = 1.0
    truth = state.truth_state

    if truth.booking_requested and not truth.booking_verified:
        score -= 0.30
        issues.append("booking was requested but never verified by a tool result")
    if truth.delivery_requested and not truth.delivery_verified:
        score -= 0.20
        issues.append("a send (intake form / details) was requested but never verified")
    if truth.last_unverified_claims or not truth.end_call_claims_verified:
        score -= 0.25
        issues.append("the agent made end-of-call claims the tools never backed")
    if state.delivery_state.last_error:
        score -= 0.10
        issues.append(f"delivery error: {state.delivery_state.last_error}")
    if state.watchdog_state.nudges_sent:
        score -= min(0.15, 0.05 * state.watchdog_state.nudges_sent)
        issues.append(f"dead-air watchdog fired {state.watchdog_state.nudges_sent}x")

    language = ""
    for turn in reversed(state.transcript):
        if turn.actor == "caller" and turn.language:
            language = turn.language
            break

    return CallReport(
        session_id=state.session_id,
        agent=agent,
        score=max(0.0, min(1.0, round(score, 3))),
        outcome="clean" if not issues else "issues",
        summary="; ".join(issues) if issues else "clean call",
        issues=issues,
        nudges=nudges,
        turns=len(state.transcript),
        language=language,
    )
