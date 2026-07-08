from __future__ import annotations

from typing import Any

from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import DecisionKinds, ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent, EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState


class UltravoxAdapter(BaseAdapter):
    provider_name = "ultravox"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_hidden_instruction_injection=True,
            supports_mid_call_prompt_patch=True,
            supports_stageful_session_updates=True,
            supports_tool_call_interception=True,
            supports_server_side_transcript_stream=True,
            supports_native_recording=True,
            supports_native_webhooks=True,
            supports_realtime_bidirectional_ws=True,
            supports_post_call_artifact_fetch=True,
        )

    async def parse_event(self, raw_event: dict[str, Any]) -> list[CanonicalEvent]:
        event_type = str(raw_event.get("type") or "").strip().lower()
        session_id = self._session_id(raw_event)
        provider_session_id = self._provider_session_id(raw_event)

        if event_type in {"session.started", "call.started", "call.created"}:
            return [
                make_event(
                    EventTypes.SESSION_STARTED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if event_type == "stage.changed":
            return [
                make_event(
                    EventTypes.STAGE_TRANSITION,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data={"stage": raw_event.get("stage")},
                )
            ]
        if event_type == "transcript":
            speaker = str(raw_event.get("speaker") or raw_event.get("role") or "").lower()
            # REST artifacts spell roles MESSAGE_ROLE_USER / MESSAGE_ROLE_AGENT
            # (verified against the live API); the realtime WS uses user/agent.
            speaker = speaker.removeprefix("message_role_")
            final = bool(raw_event.get("final", True))
            mapped_type = (
                EventTypes.CALLER_TRANSCRIPT_FINAL
                if speaker in {"caller", "user", "client"}
                else EventTypes.AGENT_TRANSCRIPT_FINAL
            )
            if not final:
                mapped_type = (
                    EventTypes.CALLER_TRANSCRIPT_PARTIAL
                    if speaker in {"caller", "user", "client"}
                    else EventTypes.AGENT_TRANSCRIPT_PARTIAL
                )
            return [
                make_event(
                    mapped_type,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="caller" if "caller" in mapped_type else "agent",
                    text=str(raw_event.get("text") or ""),
                    data=raw_event,
                )
            ]
        if event_type == "tool_call":
            return [
                make_event(
                    EventTypes.TOOL_CALLED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="tool",
                    data={"tool_name": raw_event.get("name"), **raw_event},
                )
            ]
        if event_type == "tool_result":
            return [
                make_event(
                    EventTypes.TOOL_RESULT,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="tool",
                    data={"tool_name": raw_event.get("tool_name"), **raw_event.get("result", {}), **raw_event},
                )
            ]
        if event_type == "recording.ready":
            return [
                make_event(
                    EventTypes.RECORDING_AVAILABLE,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data={"recording_url": raw_event.get("recording_url")},
                )
            ]
        if event_type == "transcript.ready":
            return [
                make_event(
                    EventTypes.TRANSCRIPT_AVAILABLE,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if event_type in {"session.ended", "call.ended"}:
            return [
                make_event(
                    EventTypes.SESSION_ENDED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        return []

    async def compile(
        self,
        decision: RuntimeDecision,
        state: RuntimeState,
    ) -> list[ProviderAction]:
        if decision.kind == DecisionKinds.INJECT_HIDDEN_INSTRUCTION:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="inject_message",
                    payload={"message": f"<instruction>{decision.payload['text']}</instruction>"},
                )
            ]
        if decision.kind == DecisionKinds.FORCE_STAGE_TRANSITION:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="change_stage",
                    payload={"stage": decision.payload["stage"]},
                )
            ]
        if decision.kind == DecisionKinds.REQUEST_FIELD_REPAIR:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="inject_message",
                    payload={"message": decision.payload["message"]},
                )
            ]
        if decision.kind == DecisionKinds.REQUEST_AVAILABILITY_WINDOW:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="set_session_context",
                    payload=decision.payload,
                )
            ]
        if decision.kind == DecisionKinds.BLOCK_DELIVERY_UNTIL_CONSENT:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="block_tool",
                    payload=decision.payload,
                )
            ]
        if decision.kind == DecisionKinds.RECONCILE_CALL_SUMMARY:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="sanitize_summary",
                    payload=decision.payload,
                )
            ]
        return []
