from __future__ import annotations

from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import DecisionKinds, ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState


class GPTRealtimeAdapter(BaseAdapter):
    provider_name = "gpt_realtime"

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

    async def parse_event(self, raw_event: dict) -> list:
        event_type = str(raw_event.get("type") or "").strip().lower()
        session_id = self._session_id(raw_event)
        provider_session_id = self._provider_session_id(raw_event)

        if event_type in {"session.created", "session.updated"}:
            mapped = EventTypes.SESSION_STARTED if event_type == "session.created" else EventTypes.SESSION_UPDATED
            return [
                make_event(
                    mapped,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        # conversation.item.created is retained in GA; conversation.item.done is
        # the GA completion event (item.added fires at in_progress — skipped to
        # avoid double-ingesting the same item).
        if event_type in {"conversation.item.created", "conversation.item.done"}:
            item = raw_event.get("item", {})
            role = str(item.get("role") or "").lower()
            text = self._item_text(item)
            if not text:
                return []
            if role == "system":
                return []
            if role == "user":
                mapped = EventTypes.CALLER_TRANSCRIPT_FINAL
                actor = "caller"
            else:
                mapped = EventTypes.AGENT_TRANSCRIPT_FINAL
                actor = "agent"
            return [
                make_event(
                    mapped,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor=actor,
                    text=text,
                    data=raw_event,
                )
            ]
        # Agent speech transcript: GA renamed response.audio_transcript.* to
        # response.output_audio_transcript.* (beta names removed 2026-05-12);
        # both are accepted.
        if event_type in {
            "response.audio_transcript.delta",
            "response.output_audio_transcript.delta",
        }:
            return [
                make_event(
                    EventTypes.AGENT_TRANSCRIPT_PARTIAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="agent",
                    text=str(raw_event.get("delta") or ""),
                    data=raw_event,
                )
            ]
        if event_type in {
            "response.audio_transcript.done",
            "response.output_audio_transcript.done",
        }:
            return [
                make_event(
                    EventTypes.AGENT_TRANSCRIPT_FINAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="agent",
                    text=str(raw_event.get("transcript") or ""),
                    data=raw_event,
                )
            ]
        # Caller speech arrives via input-audio transcription events (unchanged in GA).
        if event_type == "conversation.item.input_audio_transcription.delta":
            return [
                make_event(
                    EventTypes.CALLER_TRANSCRIPT_PARTIAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="caller",
                    text=str(raw_event.get("delta") or ""),
                    data=raw_event,
                )
            ]
        if event_type == "conversation.item.input_audio_transcription.completed":
            return [
                make_event(
                    EventTypes.CALLER_TRANSCRIPT_FINAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="caller",
                    text=str(raw_event.get("transcript") or ""),
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
        if event_type == "conversation.item.function_call_output":
            payload = dict(raw_event.get("output") or {})
            payload["tool_name"] = raw_event.get("name")
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
        if event_type == "response.completed":
            return [
                make_event(
                    EventTypes.SESSION_UPDATED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        return []

    @staticmethod
    def _item_text(item: dict) -> str:
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

    async def compile(
        self,
        decision: RuntimeDecision,
        state: RuntimeState,
    ) -> list[ProviderAction]:
        if decision.kind == DecisionKinds.INJECT_HIDDEN_INSTRUCTION:
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
                                {"type": "input_text", "text": decision.payload["text"]}
                            ],
                        },
                    },
                )
            ]
        if decision.kind == DecisionKinds.FORCE_STAGE_TRANSITION:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="session_update",
                    payload={"metadata": {"stage": decision.payload["stage"]}},
                )
            ]
        if decision.kind == DecisionKinds.REQUEST_AVAILABILITY_WINDOW:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="session_update",
                    payload={"metadata": decision.payload},
                )
            ]
        if decision.kind == DecisionKinds.BLOCK_DELIVERY_UNTIL_CONSENT:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="tool_guard",
                    payload=decision.payload,
                )
            ]
        if decision.kind == DecisionKinds.REQUEST_FIELD_REPAIR:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="response_create",
                    payload={
                        "type": "response.create",
                        "response": {"instructions": decision.payload["message"]},
                    },
                )
            ]
        if decision.kind == DecisionKinds.RECONCILE_CALL_SUMMARY:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="session_update",
                    payload={"summary_patch": decision.payload},
                )
            ]
        return []
