from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventTypes:
    SESSION_STARTED = "session.started"
    SESSION_UPDATED = "session.updated"
    SESSION_ENDED = "session.ended"
    STAGE_TRANSITION = "stage.transition"
    CALLER_TRANSCRIPT_PARTIAL = "caller.transcript.partial"
    CALLER_TRANSCRIPT_FINAL = "caller.transcript.final"
    AGENT_TRANSCRIPT_PARTIAL = "agent.transcript.partial"
    AGENT_TRANSCRIPT_FINAL = "agent.transcript.final"
    TOOL_CALLED = "tool.called"
    TOOL_RESULT = "tool.result"
    POLICY_TRIGGERED = "policy.triggered"
    WATCHDOG_TRIGGERED = "watchdog.triggered"
    CONSENT_UPDATED = "consent.updated"
    BOOKING_UPDATED = "booking.updated"
    DELIVERY_UPDATED = "delivery.updated"
    RECORDING_AVAILABLE = "recording.available"
    TRANSCRIPT_AVAILABLE = "transcript.available"
    PROVIDER_ERROR = "provider.error"
    PROVIDER_ACTION_EXECUTED = "provider.action.executed"


class CanonicalEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid4().hex)
    type: str
    session_id: str
    provider: str
    provider_session_id: str = ""
    timestamp: datetime = Field(default_factory=utc_now)
    actor: str = ""
    text: str = ""
    turn_id: str = ""
    data: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "ignore"}


def make_event(
    event_type: str,
    *,
    session_id: str,
    provider: str,
    provider_session_id: str = "",
    actor: str = "",
    text: str = "",
    turn_id: str = "",
    data: dict[str, Any] | None = None,
) -> CanonicalEvent:
    return CanonicalEvent(
        type=event_type,
        session_id=session_id,
        provider=provider,
        provider_session_id=provider_session_id,
        actor=actor,
        text=text,
        turn_id=turn_id,
        data=data or {},
    )
