from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from supafone_labs.runtime.core.events import CanonicalEvent, EventTypes
from supafone_labs.runtime.core.policies.recovery import normalize_spoken_email
from supafone_labs.runtime.core.policies.watchdog import is_bridge_phrase


class TranscriptTurn(BaseModel):
    actor: str
    text: str
    timestamp: datetime
    partial: bool = False
    language: str = ""


class ToolCallRecord(BaseModel):
    tool_name: str
    status: str
    timestamp: datetime
    request: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)


class TruthState(BaseModel):
    booking_requested: bool = False
    booking_verified: bool = False
    delivery_requested: bool = False
    delivery_verified: bool = False
    end_call_claims_verified: bool = True
    last_verified_tool: str = ""
    last_verified_at: datetime | None = None
    last_unverified_claims: list[str] = Field(default_factory=list)


class ConsentState(BaseModel):
    sms_status: str = "not_needed"
    email_status: str = "not_needed"
    recording_status: str = "unknown"


class DeliveryState(BaseModel):
    consultation_status: str = "not_sent"
    intake_form_status: str = "not_sent"
    last_channel: str = ""
    last_error: str = ""
    repaired_fields: dict[str, str] = Field(default_factory=dict)


class WatchdogState(BaseModel):
    bridge_armed: bool = False
    bridge_text: str = ""
    bridge_armed_at: datetime | None = None
    nudges_sent: int = 0


class RecordingState(BaseModel):
    native_recording_enabled: bool = True
    transcript_capture_enabled: bool = True
    recording_available: bool = False
    recording_url: str = ""
    transcript_available: bool = False
    artifact_backfill_pending: bool = False


class RuntimeState(BaseModel):
    session_id: str
    provider: str
    provider_session_id: str = ""
    workflow_id: str = "generic_support"
    current_stage: str = "intake"
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    tool_history: list[ToolCallRecord] = Field(default_factory=list)
    truth_state: TruthState = Field(default_factory=TruthState)
    consent_state: ConsentState = Field(default_factory=ConsentState)
    delivery_state: DeliveryState = Field(default_factory=DeliveryState)
    watchdog_state: WatchdogState = Field(default_factory=WatchdogState)
    recording_state: RecordingState = Field(default_factory=RecordingState)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    trace_ids: dict[str, str] = Field(default_factory=dict)
    last_event_at: datetime | None = None
    last_caller_text: str = ""
    last_agent_text: str = ""


def build_initial_state(
    *,
    provider: str,
    session_id: str,
    provider_session_id: str = "",
    workflow_id: str = "generic_support",
) -> RuntimeState:
    return RuntimeState(
        session_id=session_id,
        provider=provider,
        provider_session_id=provider_session_id,
        workflow_id=workflow_id,
    )


def _append_transcript(
    state: RuntimeState,
    *,
    actor: str,
    text: str,
    timestamp: datetime,
    partial: bool,
    language: str = "",
) -> None:
    if not text:
        return
    state.transcript.append(
        TranscriptTurn(
            actor=actor,
            text=text,
            timestamp=timestamp,
            partial=partial,
            language=language,
        )
    )
    if actor == "caller" and not partial:
        state.last_caller_text = text
    if actor == "agent" and not partial:
        state.last_agent_text = text
        if is_bridge_phrase(text):
            state.watchdog_state.bridge_armed = True
            state.watchdog_state.bridge_text = text
            state.watchdog_state.bridge_armed_at = timestamp


def _delivery_success(result: dict[str, Any]) -> bool:
    status = str(result.get("status") or "").strip().lower()
    if status in {"sent", "delivered"}:
        return True
    notifications = result.get("notifications")
    if isinstance(notifications, dict):
        for channel in notifications.values():
            if isinstance(channel, dict) and channel.get("success") is True:
                return True
    return False


def _delivery_channel(result: dict[str, Any]) -> str:
    explicit = str(result.get("method") or result.get("channel") or "").strip().lower()
    if explicit:
        return explicit
    notifications = result.get("notifications")
    if isinstance(notifications, dict):
        for name, channel in notifications.items():
            if isinstance(channel, dict) and channel.get("success") is True:
                return str(name)
    return ""


def _apply_tool_result(state: RuntimeState, event: CanonicalEvent) -> None:
    result = dict(event.data)
    tool_name = str(result.get("tool_name") or result.get("name") or "").strip()
    status = str(result.get("status") or "").strip().lower()

    state.tool_history.append(
        ToolCallRecord(
            tool_name=tool_name or "unknown_tool",
            status=status or "unknown",
            timestamp=event.timestamp,
            result=result,
        )
    )
    state.truth_state.last_verified_tool = tool_name
    state.truth_state.last_verified_at = event.timestamp
    state.watchdog_state.bridge_armed = False

    if tool_name == "book_appointment":
        state.truth_state.booking_requested = True
        if status == "booked":
            state.truth_state.booking_verified = True

    if tool_name == "record_sms_consent" and status == "recorded":
        consent_status = str(
            result.get("sms_consent_status") or result.get("consent_status") or "granted"
        )
        state.consent_state.sms_status = consent_status

    if tool_name in {"send_consultation_details", "send_intake_form", "send_email"}:
        state.truth_state.delivery_requested = True
        state.delivery_state.last_channel = _delivery_channel(result)
        if _delivery_success(result):
            state.truth_state.delivery_verified = True
            if tool_name == "send_intake_form":
                state.delivery_state.intake_form_status = "sent"
            else:
                state.delivery_state.consultation_status = "sent"
        else:
            message = str(result.get("message") or result.get("error") or "").strip()
            if message:
                state.delivery_state.last_error = message


def reduce_event(state: RuntimeState, event: CanonicalEvent) -> RuntimeState:
    next_state = state.model_copy(deep=True)
    next_state.last_event_at = event.timestamp

    if event.provider_session_id and not next_state.provider_session_id:
        next_state.provider_session_id = event.provider_session_id

    if event.type == EventTypes.SESSION_STARTED:
        next_state.provider = event.provider
        next_state.provider_metadata.update(event.data)
    elif event.type == EventTypes.SESSION_UPDATED:
        next_state.provider_metadata.update(event.data)
    elif event.type == EventTypes.STAGE_TRANSITION:
        next_state.current_stage = str(event.data.get("stage") or next_state.current_stage)
    elif event.type == EventTypes.CALLER_TRANSCRIPT_PARTIAL:
        _append_transcript(
            next_state,
            actor="caller",
            text=event.text,
            timestamp=event.timestamp,
            partial=True,
            language=str(event.data.get("language") or ""),
        )
    elif event.type == EventTypes.CALLER_TRANSCRIPT_FINAL:
        _append_transcript(
            next_state,
            actor="caller",
            text=event.text,
            timestamp=event.timestamp,
            partial=False,
            language=str(event.data.get("language") or ""),
        )
    elif event.type == EventTypes.AGENT_TRANSCRIPT_PARTIAL:
        _append_transcript(
            next_state,
            actor="agent",
            text=event.text,
            timestamp=event.timestamp,
            partial=True,
            language=str(event.data.get("language") or ""),
        )
    elif event.type == EventTypes.AGENT_TRANSCRIPT_FINAL:
        _append_transcript(
            next_state,
            actor="agent",
            text=event.text,
            timestamp=event.timestamp,
            partial=False,
            language=str(event.data.get("language") or ""),
        )
    elif event.type == EventTypes.TOOL_CALLED:
        tool_name = str(event.data.get("tool_name") or event.data.get("name") or "unknown_tool")
        next_state.tool_history.append(
            ToolCallRecord(
                tool_name=tool_name,
                status="requested",
                timestamp=event.timestamp,
                request=dict(event.data),
            )
        )
        if tool_name == "book_appointment":
            next_state.truth_state.booking_requested = True
        if tool_name in {"send_consultation_details", "send_intake_form", "send_email"}:
            next_state.truth_state.delivery_requested = True
    elif event.type == EventTypes.TOOL_RESULT:
        _apply_tool_result(next_state, event)
    elif event.type == EventTypes.CONSENT_UPDATED:
        channel = str(event.data.get("channel") or "").strip().lower()
        status = str(event.data.get("status") or "").strip().lower()
        if channel == "sms":
            next_state.consent_state.sms_status = status
        elif channel == "email":
            next_state.consent_state.email_status = status
        elif channel == "recording":
            next_state.consent_state.recording_status = status
    elif event.type == EventTypes.DELIVERY_UPDATED:
        channel = str(event.data.get("channel") or "").strip().lower()
        status = str(event.data.get("status") or "").strip().lower()
        next_state.delivery_state.last_channel = channel
        if event.data.get("kind") == "intake_form":
            next_state.delivery_state.intake_form_status = status
        else:
            next_state.delivery_state.consultation_status = status
        if status in {"sent", "delivered"}:
            next_state.truth_state.delivery_verified = True
    elif event.type == EventTypes.RECORDING_AVAILABLE:
        next_state.recording_state.recording_available = True
        next_state.recording_state.recording_url = str(event.data.get("recording_url") or "")
        next_state.recording_state.artifact_backfill_pending = False
    elif event.type == EventTypes.TRANSCRIPT_AVAILABLE:
        next_state.recording_state.transcript_available = True
        next_state.recording_state.artifact_backfill_pending = False
    elif event.type == EventTypes.PROVIDER_ERROR:
        next_state.provider_metadata["last_error"] = event.data or {"message": event.text}
    elif event.type == EventTypes.WATCHDOG_TRIGGERED:
        next_state.watchdog_state.bridge_armed = False
        next_state.watchdog_state.nudges_sent += 1
    elif event.type == EventTypes.SESSION_ENDED:
        next_state.provider_metadata["session_ended"] = True

    if "email" in str(event.data.get("field") or "").lower():
        repaired = normalize_spoken_email(str(event.data.get("value") or ""))
        if repaired:
            next_state.delivery_state.repaired_fields["email"] = repaired

    return next_state


def apply_events(events: list[CanonicalEvent], initial_state: RuntimeState) -> RuntimeState:
    state = initial_state
    for event in events:
        state = reduce_event(state, event)
    return state
