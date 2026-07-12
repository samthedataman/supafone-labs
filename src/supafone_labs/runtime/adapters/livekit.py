"""LiveKit Agents adapter — AgentSession events from a framework you host.

LiveKit Agents runs in your process; the ``AgentSession`` emits typed events:
``user_input_transcribed`` (with ``transcript`` + ``is_final``),
``conversation_item_added`` (a committed user/assistant item),
``function_tools_executed``, ``agent_state_changed``, ``close``. The tap accepts
those event names (snake_case) under ``type``/``event``.

Injection: you own the session object, so the compiled action is a
``chat_context_append`` — add an assistant-role message to the agent's live
``ChatContext`` before its next inference turn. Realtime models VOICE an
appended ``system`` item; ``assistant`` is LiveKit's canonical silent-context
role, so it steers the next turn without being spoken.
"""
from __future__ import annotations

from typing import Any

from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import DecisionKinds, ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent, EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState


class LivekitAdapter(BaseAdapter):
    provider_name = "livekit"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_hidden_instruction_injection=True,   # ChatContext append
            supports_mid_call_prompt_patch=True,
            supports_stageful_session_updates=True,
            supports_tool_call_interception=True,
            supports_server_side_transcript_stream=True,
            supports_native_recording=True,               # via Egress
            supports_native_webhooks=True,
            supports_realtime_bidirectional_ws=True,
            supports_post_call_artifact_fetch=True,
        )

    def _event_name(self, raw_event: dict[str, Any]) -> str:
        return str(raw_event.get("type") or raw_event.get("event") or "").strip().lower()

    async def parse_event(self, raw_event: dict[str, Any]) -> list[CanonicalEvent]:
        name = self._event_name(raw_event)
        session_id = self._session_id(raw_event)
        provider_session_id = self._provider_session_id(raw_event) or str(
            raw_event.get("room") or raw_event.get("room_name") or ""
        )

        if name in {"session_started", "agent_session_started", "room_started"}:
            return [
                make_event(
                    EventTypes.SESSION_STARTED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if name == "user_input_transcribed":
            final = bool(raw_event.get("is_final", True))
            return [
                make_event(
                    EventTypes.CALLER_TRANSCRIPT_FINAL if final else EventTypes.CALLER_TRANSCRIPT_PARTIAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="caller",
                    text=str(raw_event.get("transcript") or raw_event.get("text") or ""),
                    data=raw_event,
                )
            ]
        if name == "conversation_item_added":
            item = raw_event.get("item") if isinstance(raw_event.get("item"), dict) else raw_event
            role = str(item.get("role") or "").lower()
            text = str(item.get("text_content") or item.get("content") or item.get("text") or "")
            if not text:
                return []  # item union includes AgentHandoff, which has no text
            caller = role == "user"
            return [
                make_event(
                    EventTypes.CALLER_TRANSCRIPT_FINAL if caller else EventTypes.AGENT_TRANSCRIPT_FINAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="caller" if caller else "agent",
                    text=text,
                    data=raw_event,
                )
            ]
        if name == "function_tools_executed":
            events: list[CanonicalEvent] = []
            calls = raw_event.get("function_calls")
            outputs = raw_event.get("function_call_outputs")
            for call in calls if isinstance(calls, list) else []:
                events.append(
                    make_event(
                        EventTypes.TOOL_CALLED,
                        session_id=session_id,
                        provider=self.provider_name,
                        provider_session_id=provider_session_id,
                        actor="tool",
                        data={"tool_name": (call or {}).get("name"), **(call or {})},
                    )
                )
            for output in outputs if isinstance(outputs, list) else []:
                events.append(
                    make_event(
                        EventTypes.TOOL_RESULT,
                        session_id=session_id,
                        provider=self.provider_name,
                        provider_session_id=provider_session_id,
                        actor="tool",
                        data={"tool_name": (output or {}).get("name"), **(output or {})},
                    )
                )
            return events
        if name in {"close", "session_ended", "room_finished"}:
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
        if decision.kind in {
            DecisionKinds.INJECT_HIDDEN_INSTRUCTION,
            DecisionKinds.REQUEST_FIELD_REPAIR,
        }:
            text = decision.payload.get("text") or decision.payload.get("message") or ""
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="chat_context_append",
                    payload={"role": "assistant", "content": text},
                )
            ]
        if decision.kind == DecisionKinds.FORCE_STAGE_TRANSITION:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="chat_context_append",
                    payload={
                        "role": "assistant",
                        "content": f"Conversation stage is now: {decision.payload['stage']}",
                    },
                )
            ]
        if decision.kind == DecisionKinds.REQUEST_AVAILABILITY_WINDOW:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="chat_context_append",
                    payload={"role": "assistant", "content": str(decision.payload)},
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
