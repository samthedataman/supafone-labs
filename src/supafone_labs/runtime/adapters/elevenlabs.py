"""ElevenLabs Conversational AI adapter — websocket events + contextual updates.

ElevenLabs runs a full agent (STT -> LLM -> TTS) and streams typed websocket
events: ``conversation_initiation_metadata``, ``user_transcript`` (inside a
``user_transcription_event``), ``agent_response`` (inside an
``agent_response_event``), ``client_tool_call``, ``interruption``, plus a
``post_call_transcription`` webhook after the call.

Injection is first-class: a ``contextual_update`` message is text the agent
*reads but never speaks* — exactly Supafone Labs' hidden-instruction semantics.
"""
from __future__ import annotations

from typing import Any

from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import DecisionKinds, ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent, EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState


class ElevenLabsAdapter(BaseAdapter):
    provider_name = "elevenlabs"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_hidden_instruction_injection=True,
            supports_mid_call_prompt_patch=True,
            supports_stageful_session_updates=False,
            supports_tool_call_interception=True,
            supports_server_side_transcript_stream=True,
            supports_native_recording=True,
            supports_native_webhooks=True,
            supports_realtime_bidirectional_ws=True,
            supports_post_call_artifact_fetch=True,
        )

    def _provider_session_id(self, raw_event: dict[str, Any]) -> str:
        meta = raw_event.get("conversation_initiation_metadata_event")
        if isinstance(meta, dict) and meta.get("conversation_id"):
            return str(meta["conversation_id"])
        return str(
            raw_event.get("provider_session_id") or raw_event.get("conversation_id") or ""
        )

    async def parse_event(self, raw_event: dict[str, Any]) -> list[CanonicalEvent]:
        event_type = str(raw_event.get("type") or "").strip().lower()
        session_id = self._session_id(raw_event)
        provider_session_id = self._provider_session_id(raw_event)

        if event_type == "conversation_initiation_metadata":
            return [
                make_event(
                    EventTypes.SESSION_STARTED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if event_type == "user_transcript":
            inner = raw_event.get("user_transcription_event") or {}
            return [
                make_event(
                    EventTypes.CALLER_TRANSCRIPT_FINAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="caller",
                    text=str(inner.get("user_transcript") or raw_event.get("text") or ""),
                    data=raw_event,
                )
            ]
        if event_type == "tentative_agent_response":  # legacy, pre-eleven-agents docs
            inner = raw_event.get("tentative_agent_response_internal_event") or {}
            return [
                make_event(
                    EventTypes.AGENT_TRANSCRIPT_PARTIAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="agent",
                    text=str(inner.get("tentative_agent_response") or ""),
                    data=raw_event,
                )
            ]
        # Current streaming agent text: agent_chat_response_part with a
        # text_response_part {type: start|delta|stop, text}.
        if event_type == "agent_chat_response_part":
            inner = raw_event.get("text_response_part") or {}
            text = str(inner.get("text") or "")
            if not text:
                return []
            return [
                make_event(
                    EventTypes.AGENT_TRANSCRIPT_PARTIAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="agent",
                    text=text,
                    data=raw_event,
                )
            ]
        # The agent's spoken text was revised after an interruption — the
        # corrected text is what the caller actually heard.
        if event_type == "agent_response_correction":
            inner = raw_event.get("agent_response_correction_event") or {}
            return [
                make_event(
                    EventTypes.AGENT_TRANSCRIPT_FINAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="agent",
                    text=str(inner.get("corrected_agent_response") or ""),
                    data=raw_event,
                )
            ]
        if event_type == "agent_response":
            inner = raw_event.get("agent_response_event") or {}
            return [
                make_event(
                    EventTypes.AGENT_TRANSCRIPT_FINAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="agent",
                    text=str(inner.get("agent_response") or raw_event.get("text") or ""),
                    data=raw_event,
                )
            ]
        if event_type == "client_tool_call":
            inner = raw_event.get("client_tool_call") or {}
            return [
                make_event(
                    EventTypes.TOOL_CALLED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="tool",
                    data={"tool_name": inner.get("tool_name"), **inner},
                )
            ]
        if event_type == "client_tool_result":
            inner = raw_event.get("client_tool_result") or {}
            payload = dict(inner.get("result") or {})
            payload["tool_name"] = inner.get("tool_name") or raw_event.get("tool_name")
            return [
                make_event(
                    EventTypes.TOOL_RESULT,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="tool",
                    data=payload,
                )
            ]
        if event_type == "post_call_transcription":
            return [
                make_event(
                    EventTypes.TRANSCRIPT_AVAILABLE,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                ),
                make_event(
                    EventTypes.SESSION_ENDED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                ),
            ]
        # audio / ping / interruption / vad_score are transport chatter, not state.
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
                    kind="contextual_update",
                    payload={"type": "contextual_update", "text": decision.payload["text"]},
                )
            ]
        if decision.kind == DecisionKinds.REQUEST_FIELD_REPAIR:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="contextual_update",
                    payload={"type": "contextual_update", "text": decision.payload["message"]},
                )
            ]
        if decision.kind == DecisionKinds.FORCE_STAGE_TRANSITION:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="contextual_update",
                    payload={
                        "type": "contextual_update",
                        "text": f"Conversation stage is now: {decision.payload['stage']}",
                    },
                )
            ]
        if decision.kind == DecisionKinds.REQUEST_AVAILABILITY_WINDOW:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="contextual_update",
                    payload={"type": "contextual_update", "text": str(decision.payload)},
                )
            ]
        if decision.kind == DecisionKinds.BLOCK_DELIVERY_UNTIL_CONSENT:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="deny_tool_request",
                    payload=decision.payload,
                )
            ]
        if decision.kind == DecisionKinds.RECONCILE_CALL_SUMMARY:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="summary_patch",
                    payload=decision.payload,
                )
            ]
        return []
