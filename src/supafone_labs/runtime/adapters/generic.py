"""GenericWebhookAdapter — last-resort best-effort mapping for unknown agents.

For a provider without a dedicated adapter, this maps common webhook shapes by
convention: a ``type``/``event`` field with start/end keywords, transcript-ish
payloads (``text`` / ``transcript`` / ``message`` + ``role`` / ``speaker``),
and tool-ish payloads (``tool`` / ``function`` / ``name`` keys). The injection
action kind is configurable so the caller can name whatever control their
provider exposes.
"""
from __future__ import annotations

from typing import Any

from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import DecisionKinds, ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent, EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState

_START_HINTS = {"start", "started", "created", "begin", "connected", "initiation"}
_END_HINTS = {"end", "ended", "stop", "stopped", "complete", "completed", "hangup", "disconnected"}
_CALLER_HINTS = {"caller", "user", "client", "customer", "human", "inbound"}


class GenericWebhookAdapter(BaseAdapter):
    provider_name = "generic"

    def __init__(
        self,
        provider_name: str | None = None,
        inject_action_kind: str = "inject",
        inject_text_key: str = "text",
    ) -> None:
        if provider_name:
            self.provider_name = provider_name
        self.inject_action_kind = inject_action_kind
        self.inject_text_key = inject_text_key

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_hidden_instruction_injection=True,  # configurable, best-effort
            supports_mid_call_prompt_patch=False,
            supports_stageful_session_updates=False,
            supports_tool_call_interception=False,
            supports_server_side_transcript_stream=True,
            supports_native_recording=False,
            supports_native_webhooks=True,
            supports_realtime_bidirectional_ws=False,
            supports_post_call_artifact_fetch=False,
        )

    def _text_of(self, raw_event: dict[str, Any]) -> str:
        for key in ("text", "transcript", "message", "content", "utterance"):
            value = raw_event.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return ""

    def _is_caller(self, raw_event: dict[str, Any]) -> bool:
        for key in ("role", "speaker", "actor", "from", "participant"):
            value = str(raw_event.get(key) or "").strip().lower()
            if value:
                return value in _CALLER_HINTS
        return True  # unknown speaker: assume the caller, the safer tap default

    async def parse_event(self, raw_event: dict[str, Any]) -> list[CanonicalEvent]:
        event_type = str(raw_event.get("type") or raw_event.get("event") or "").strip().lower()
        session_id = self._session_id(raw_event)
        provider_session_id = self._provider_session_id(raw_event)
        tokens = set(event_type.replace("-", "_").replace(".", "_").split("_"))

        if tokens & _START_HINTS:
            return [
                make_event(
                    EventTypes.SESSION_STARTED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if tokens & _END_HINTS:
            return [
                make_event(
                    EventTypes.SESSION_ENDED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if "tool" in tokens or "function" in tokens:
            data = {"tool_name": raw_event.get("tool") or raw_event.get("function") or raw_event.get("name"), **raw_event}
            mapped = EventTypes.TOOL_RESULT if "result" in tokens or "output" in tokens else EventTypes.TOOL_CALLED
            return [
                make_event(
                    mapped,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="tool",
                    data=data,
                )
            ]
        text = self._text_of(raw_event)
        if text:
            caller = self._is_caller(raw_event)
            final = bool(raw_event.get("final", raw_event.get("is_final", True)))
            if caller:
                mapped = (
                    EventTypes.CALLER_TRANSCRIPT_FINAL if final else EventTypes.CALLER_TRANSCRIPT_PARTIAL
                )
            else:
                mapped = (
                    EventTypes.AGENT_TRANSCRIPT_FINAL if final else EventTypes.AGENT_TRANSCRIPT_PARTIAL
                )
            return [
                make_event(
                    mapped,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="caller" if caller else "agent",
                    text=text,
                    data=raw_event,
                )
            ]
        return []

    async def compile(
        self,
        decision: RuntimeDecision,
        state: RuntimeState,
    ) -> list[ProviderAction]:
        if decision.kind in {
            DecisionKinds.INJECT_HIDDEN_INSTRUCTION,
            DecisionKinds.REQUEST_FIELD_REPAIR,
        }:
            text = decision.payload.get("text") or decision.payload.get("message") or ""
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind=self.inject_action_kind,
                    payload={self.inject_text_key: text},
                )
            ]
        if decision.kind == DecisionKinds.FORCE_STAGE_TRANSITION:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind=self.inject_action_kind,
                    payload={self.inject_text_key: f"Conversation stage is now: {decision.payload['stage']}"},
                )
            ]
        # Availability windows, consent blocks and summary reconciliation need
        # provider-specific controls a generic webhook can't promise.
        return []
