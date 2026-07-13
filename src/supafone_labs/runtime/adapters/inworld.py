"""Inworld Realtime adapter with legacy character-event compatibility.

Inworld's current Realtime API follows the OpenAI Realtime event protocol and
accepts system-role conversation items during a call. Older character-engine
``text`` packets are still parsed so existing integrations keep working.
"""
from __future__ import annotations

from typing import Any

from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import DecisionKinds, ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent, EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState


class InworldAdapter(BaseAdapter):
    provider_name = "inworld"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_hidden_instruction_injection=True,
            supports_mid_call_prompt_patch=True,
            supports_stageful_session_updates=True,
            supports_tool_call_interception=True,
            supports_server_side_transcript_stream=True,
            supports_native_recording=False,
            supports_native_webhooks=False,
            supports_realtime_bidirectional_ws=True,
            supports_post_call_artifact_fetch=False,
        )

    def _is_player(self, raw_event: dict[str, Any]) -> bool:
        routing = raw_event.get("routing") if isinstance(raw_event.get("routing"), dict) else {}
        source = routing.get("source") if isinstance(routing.get("source"), dict) else {}
        if isinstance(source.get("isPlayer"), bool):
            return bool(source["isPlayer"])
        speaker = str(raw_event.get("speaker") or raw_event.get("role") or "").lower()
        return speaker in {"player", "user", "caller", "client"}

    @staticmethod
    def _item_text(item: dict[str, Any]) -> str:
        if item.get("text"):
            return str(item["text"])
        content = item.get("content")
        if isinstance(content, str):
            return content
        if not isinstance(content, list):
            return ""
        return "".join(
            str(part.get("text") or part.get("transcript") or "")
            for part in content
            if isinstance(part, dict)
        )

    async def parse_event(self, raw_event: dict[str, Any]) -> list[CanonicalEvent]:
        event_type = str(raw_event.get("type") or "").strip().lower()
        session_id = self._session_id(raw_event)
        provider_session_id = self._provider_session_id(raw_event) or str(
            raw_event.get("interaction_id") or raw_event.get("interactionId") or ""
        )

        if event_type in {
            "session.created",
            "session_start",
            "session.started",
            "control_session_start",
        }:
            return [
                make_event(
                    EventTypes.SESSION_STARTED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if event_type == "session.updated":
            return [
                make_event(
                    EventTypes.SESSION_UPDATED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if event_type in {
            "conversation.item.added",
            "conversation.item.created",
            "conversation.item.done",
        }:
            item = raw_event.get("item") if isinstance(raw_event.get("item"), dict) else {}
            if event_type == "conversation.item.added" and item.get("status") != "completed":
                # Current Inworld sessions emit added and then done for one item.
                # Only a completed added event is safe to treat as a final turn.
                return []
            role = str(item.get("role") or "").lower()
            text = self._item_text(item)
            if not text or role == "system":
                return []
            caller = role == "user"
            return [
                make_event(
                    EventTypes.CALLER_TRANSCRIPT_FINAL
                    if caller
                    else EventTypes.AGENT_TRANSCRIPT_FINAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="caller" if caller else "agent",
                    text=text,
                    data=raw_event,
                )
            ]
        if event_type in {
            "conversation.item.input_audio_transcription.delta",
            "conversation.item.input_audio_transcription.completed",
        }:
            final = event_type.endswith("completed")
            return [
                make_event(
                    EventTypes.CALLER_TRANSCRIPT_FINAL
                    if final
                    else EventTypes.CALLER_TRANSCRIPT_PARTIAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="caller",
                    text=str(raw_event.get("transcript") or raw_event.get("delta") or ""),
                    data=raw_event,
                )
            ]
        if event_type in {
            "response.output_audio_transcript.delta",
            "response.output_audio_transcript.done",
            "response.output_text.delta",
            "response.output_text.done",
        }:
            final = event_type.endswith("done")
            return [
                make_event(
                    EventTypes.AGENT_TRANSCRIPT_FINAL
                    if final
                    else EventTypes.AGENT_TRANSCRIPT_PARTIAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="agent",
                    text=str(
                        raw_event.get("transcript")
                        or raw_event.get("text")
                        or raw_event.get("delta")
                        or ""
                    ),
                    data=raw_event,
                )
            ]
        if event_type == "response.function_call_arguments.done":
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
        if event_type == "text":
            body = raw_event.get("text")
            if isinstance(body, dict):
                text = str(body.get("text") or "")
                final = bool(body.get("final", True))
            else:
                text = str(body or "")
                final = bool(raw_event.get("final", True))
            if not text.strip():
                return []
            caller = self._is_player(raw_event)
            return [
                make_event(
                    (
                        EventTypes.CALLER_TRANSCRIPT_FINAL
                        if final
                        else EventTypes.CALLER_TRANSCRIPT_PARTIAL
                    )
                    if caller
                    else (
                        EventTypes.AGENT_TRANSCRIPT_FINAL
                        if final
                        else EventTypes.AGENT_TRANSCRIPT_PARTIAL
                    ),
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="caller" if caller else "agent",
                    text=text,
                    data=raw_event,
                )
            ]
        if event_type in {"session_end", "session.ended", "control_session_end"}:
            return [
                make_event(
                    EventTypes.SESSION_ENDED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if event_type == "error":
            return [
                make_event(
                    EventTypes.PROVIDER_ERROR,
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
        if decision.kind in {
            DecisionKinds.INJECT_HIDDEN_INSTRUCTION,
            DecisionKinds.REQUEST_FIELD_REPAIR,
        }:
            text = decision.payload.get("text") or decision.payload.get("message") or ""
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="conversation_item_create",
                    payload={
                        "type": "conversation.item.create",
                        "item": {
                            "type": "message",
                            "role": "system",
                            "content": [{"type": "input_text", "text": text}],
                        },
                    },
                )
            ]
        if decision.kind == DecisionKinds.FORCE_STAGE_TRANSITION:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="conversation_item_create",
                    payload={
                        "type": "conversation.item.create",
                        "item": {
                            "type": "message",
                            "role": "system",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": f"Conversation stage is now: {decision.payload['stage']}",
                                }
                            ],
                        },
                    },
                )
            ]
        return []
