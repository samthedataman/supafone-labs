"""Google Gemini Live API adapter — speech-to-speech over a realtime websocket.

The Live API (``wss://.../BidiGenerateContent``) streams server messages as
``BidiGenerateContentServerMessage`` frames: ``setupComplete`` (handshake done),
``serverContent`` (which carries ``inputTranscription`` for the caller's audio,
``outputTranscription`` for the model's spoken audio, a streamed ``modelTurn``
of text ``parts``, and ``turnComplete``), ``toolCall`` (``functionCalls``), and
``goAway`` (the connection is about to close). Roles in Gemini content are ONLY
``user``/``model`` — never ``system``.

Injection: you hold the bidi socket, so the compiled action is a
``send_client_content`` — append a ``user``-role turn with ``turnComplete:false``
so the instruction steers the next model turn silently, without ending the turn
or being voiced back to the caller.
"""
from __future__ import annotations

from typing import Any

from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import DecisionKinds, ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent, EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState


class GeminiLiveAdapter(BaseAdapter):
    provider_name = "gemini"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_hidden_instruction_injection=True,   # send_client_content turn
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

        if "setupComplete" in raw_event or event_type in {"setup_complete", "session_start"}:
            return [
                make_event(
                    EventTypes.SESSION_STARTED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]

        server_content = raw_event.get("serverContent")
        if isinstance(server_content, dict):
            events: list[CanonicalEvent] = []
            # Caller audio STT.
            input_tx = server_content.get("inputTranscription")
            if isinstance(input_tx, dict) and input_tx.get("text"):
                events.append(
                    make_event(
                        EventTypes.CALLER_TRANSCRIPT_FINAL,
                        session_id=session_id,
                        provider=self.provider_name,
                        provider_session_id=provider_session_id,
                        actor="caller",
                        text=str(input_tx.get("text") or ""),
                        data=raw_event,
                    )
                )
            # Model audio transcript.
            output_tx = server_content.get("outputTranscription")
            if isinstance(output_tx, dict) and output_tx.get("text"):
                events.append(
                    make_event(
                        EventTypes.AGENT_TRANSCRIPT_FINAL,
                        session_id=session_id,
                        provider=self.provider_name,
                        provider_session_id=provider_session_id,
                        actor="agent",
                        text=str(output_tx.get("text") or ""),
                        data=raw_event,
                    )
                )
            # Streamed model text turn (partial until turnComplete).
            model_turn = server_content.get("modelTurn")
            if isinstance(model_turn, dict):
                parts = model_turn.get("parts")
                text = "".join(
                    str(p.get("text") or "") for p in parts if isinstance(p, dict)
                ) if isinstance(parts, list) else ""
                if text:
                    final = bool(server_content.get("turnComplete"))
                    events.append(
                        make_event(
                            EventTypes.AGENT_TRANSCRIPT_FINAL if final else EventTypes.AGENT_TRANSCRIPT_PARTIAL,
                            session_id=session_id,
                            provider=self.provider_name,
                            provider_session_id=provider_session_id,
                            actor="agent",
                            text=text,
                            data=raw_event,
                        )
                    )
            return events

        tool_call = raw_event.get("toolCall")
        if isinstance(tool_call, dict):
            events = []
            calls = tool_call.get("functionCalls")
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
            return events

        if "goAway" in raw_event or event_type in {"session_end", "close"}:
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
            # Gemini turn roles are ONLY user/model. A user-role turn with
            # turnComplete:false appends context to steer the next model turn
            # without closing the turn or being spoken back.
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="send_client_content",
                    payload={
                        "turns": [{"role": "user", "parts": [{"text": text}]}],
                        "turnComplete": False,
                    },
                )
            ]
        if decision.kind == DecisionKinds.FORCE_STAGE_TRANSITION:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="send_client_content",
                    payload={
                        "turns": [
                            {
                                "role": "user",
                                "parts": [
                                    {"text": f"Conversation stage is now: {decision.payload['stage']}"}
                                ],
                            }
                        ],
                        "turnComplete": False,
                    },
                )
            ]
        if decision.kind == DecisionKinds.REQUEST_AVAILABILITY_WINDOW:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="send_client_content",
                    payload={
                        "turns": [{"role": "user", "parts": [{"text": str(decision.payload)}]}],
                        "turnComplete": False,
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
