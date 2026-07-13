"""Gemini Live adapter for bidirectional Live API sessions.

Gemini content roles are ``user`` and ``model``. Mid-session control updates
therefore use an incomplete ``user`` turn rather than an invalid ``system``
turn.
"""
from __future__ import annotations

from typing import Any

from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import DecisionKinds, ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent, EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState


def _value(mapping: dict[str, Any], camel: str, snake: str) -> Any:
    return mapping.get(camel) if camel in mapping else mapping.get(snake)


class GeminiLiveAdapter(BaseAdapter):
    provider_name = "gemini_live"

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

    async def parse_event(self, raw_event: dict[str, Any]) -> list[CanonicalEvent]:
        session_id = self._session_id(raw_event)
        provider_session_id = self._provider_session_id(raw_event)
        event_type = str(raw_event.get("type") or "").strip().lower()
        if (
            _value(raw_event, "setupComplete", "setup_complete") is not None
            or event_type in {"setup_complete", "session_start"}
        ):
            return [
                make_event(
                    EventTypes.SESSION_STARTED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]

        server_content = _value(raw_event, "serverContent", "server_content")
        if isinstance(server_content, dict):
            events: list[CanonicalEvent] = []
            input_tx = _value(server_content, "inputTranscription", "input_transcription")
            if isinstance(input_tx, dict) and input_tx.get("text"):
                interim_value = _value(
                    server_content,
                    "interimInputTranscription",
                    "interim_input_transcription",
                )
                turn_complete = bool(_value(server_content, "turnComplete", "turn_complete"))
                final = not bool(interim_value) if interim_value is not None else turn_complete
                events.append(
                    make_event(
                        EventTypes.CALLER_TRANSCRIPT_FINAL
                        if final
                        else EventTypes.CALLER_TRANSCRIPT_PARTIAL,
                        session_id=session_id,
                        provider=self.provider_name,
                        provider_session_id=provider_session_id,
                        actor="caller",
                        text=str(input_tx["text"]),
                        data=raw_event,
                    )
                )
            output_tx = _value(server_content, "outputTranscription", "output_transcription")
            if isinstance(output_tx, dict) and output_tx.get("text"):
                events.append(
                    make_event(
                        EventTypes.AGENT_TRANSCRIPT_FINAL,
                        session_id=session_id,
                        provider=self.provider_name,
                        provider_session_id=provider_session_id,
                        actor="agent",
                        text=str(output_tx["text"]),
                        data=raw_event,
                    )
                )
            model_turn = _value(server_content, "modelTurn", "model_turn")
            if isinstance(model_turn, dict):
                parts = model_turn.get("parts")
                text = "".join(
                    str(part.get("text") or "")
                    for part in (parts if isinstance(parts, list) else [])
                    if isinstance(part, dict)
                )
                if text:
                    final = bool(_value(server_content, "turnComplete", "turn_complete"))
                    events.append(
                        make_event(
                            EventTypes.AGENT_TRANSCRIPT_FINAL
                            if final
                            else EventTypes.AGENT_TRANSCRIPT_PARTIAL,
                            session_id=session_id,
                            provider=self.provider_name,
                            provider_session_id=provider_session_id,
                            actor="agent",
                            text=text,
                            data=raw_event,
                        )
                    )
            return events

        tool_call = _value(raw_event, "toolCall", "tool_call")
        if isinstance(tool_call, dict):
            calls = _value(tool_call, "functionCalls", "function_calls")
            return [
                make_event(
                    EventTypes.TOOL_CALLED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="tool",
                    data={"tool_name": call.get("name"), **call},
                )
                for call in (calls if isinstance(calls, list) else [])
                if isinstance(call, dict)
            ]
        if (
            _value(raw_event, "goAway", "go_away") is not None
            or event_type in {"session_end", "close"}
        ):
            return [
                make_event(
                    EventTypes.SESSION_ENDED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if raw_event.get("error"):
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
                    kind="client_content",
                    payload={
                        "clientContent": {
                            "turns": [{"role": "user", "parts": [{"text": text}]}],
                            "turnComplete": False,
                        }
                    },
                )
            ]
        if decision.kind == DecisionKinds.FORCE_STAGE_TRANSITION:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="client_content",
                    payload={
                        "clientContent": {
                            "turns": [
                                {
                                    "role": "user",
                                    "parts": [
                                        {
                                            "text": f"Conversation stage is now: {decision.payload['stage']}"
                                        }
                                    ],
                                }
                            ],
                            "turnComplete": False,
                        }
                    },
                )
            ]
        if decision.kind == DecisionKinds.REQUEST_AVAILABILITY_WINDOW:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="client_content",
                    payload={
                        "clientContent": {
                            "turns": [
                                {
                                    "role": "user",
                                    "parts": [{"text": str(decision.payload)}],
                                }
                            ],
                            "turnComplete": False,
                        }
                    },
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
        if decision.kind == DecisionKinds.RECONCILE_CALL_SUMMARY:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="summary_patch",
                    payload=decision.payload,
                )
            ]
        return []
