"""Pipecat adapter — frame-based agent framework (you own the pipeline).

Pipecat is not a hosted agent: your process runs a frame pipeline
(STT -> LLM -> TTS). The tap accepts serialized frames — either the frame class
name (``TranscriptionFrame``, ``InterimTranscriptionFrame``, ``TTSTextFrame``,
``BotStoppedSpeakingFrame``, ``FunctionCallInProgressFrame``,
``FunctionCallResultFrame``, ``EndFrame``) under a ``frame`` key, or the
snake_case ``type`` equivalents.

Injection: because you own the pipeline, the compiled action is an
``append_context_frame`` — push an ``LLMMessagesAppendFrame`` with a
system-role message into the live context before the next LLM turn.
"""
from __future__ import annotations

from typing import Any

from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import DecisionKinds, ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent, EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState

_FRAME_ALIASES = {
    "transcriptionframe": "transcription",
    "interimtranscriptionframe": "interim_transcription",
    "ttstextframe": "tts_text",
    "textframe": "tts_text",
    "llmtextframe": "llm_text",
    "botstoppedspeakingframe": "bot_stopped_speaking",
    "functioncallinprogressframe": "function_call",
    "functioncallresultframe": "function_call_result",
    "startframe": "start",
    "endframe": "end",
    "cancelframe": "end",
}


class PipecatAdapter(BaseAdapter):
    provider_name = "pipecat"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_hidden_instruction_injection=True,   # LLMMessagesAppendFrame
            supports_mid_call_prompt_patch=True,
            supports_stageful_session_updates=True,
            supports_tool_call_interception=True,
            supports_server_side_transcript_stream=True,
            supports_native_recording=False,
            supports_native_webhooks=False,
            supports_realtime_bidirectional_ws=True,
            supports_post_call_artifact_fetch=False,
        )

    def _frame_kind(self, raw_event: dict[str, Any]) -> str:
        frame = str(raw_event.get("frame") or raw_event.get("type") or "").strip()
        lowered = frame.lower().replace("-", "_")
        return _FRAME_ALIASES.get(lowered.replace("_", ""), lowered)

    async def parse_event(self, raw_event: dict[str, Any]) -> list[CanonicalEvent]:
        kind = self._frame_kind(raw_event)
        session_id = self._session_id(raw_event)
        provider_session_id = self._provider_session_id(raw_event)

        if kind == "start":
            return [
                make_event(
                    EventTypes.SESSION_STARTED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if kind == "transcription":
            return [
                make_event(
                    EventTypes.CALLER_TRANSCRIPT_FINAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="caller",
                    text=str(raw_event.get("text") or ""),
                    data=raw_event,
                )
            ]
        if kind == "interim_transcription":
            return [
                make_event(
                    EventTypes.CALLER_TRANSCRIPT_PARTIAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="caller",
                    text=str(raw_event.get("text") or ""),
                    data=raw_event,
                )
            ]
        if kind == "llm_text":
            # LLMTextFrame streams model tokens; TTSTextFrame is what's spoken.
            return [
                make_event(
                    EventTypes.AGENT_TRANSCRIPT_PARTIAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="agent",
                    text=str(raw_event.get("text") or ""),
                    data=raw_event,
                )
            ]
        if kind == "tts_text":
            return [
                make_event(
                    EventTypes.AGENT_TRANSCRIPT_FINAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="agent",
                    text=str(raw_event.get("text") or ""),
                    data=raw_event,
                )
            ]
        if kind == "function_call":
            return [
                make_event(
                    EventTypes.TOOL_CALLED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="tool",
                    data={"tool_name": raw_event.get("function_name") or raw_event.get("name"), **raw_event},
                )
            ]
        if kind == "function_call_result":
            payload = dict(raw_event.get("result") or {})
            payload["tool_name"] = raw_event.get("function_name") or raw_event.get("name")
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
        if kind == "end":
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
                    kind="append_context_frame",
                    payload={
                        "frame": "LLMMessagesAppendFrame",
                        "messages": [{"role": "system", "content": text}],
                        # whisper lands silently; don't force a new model turn
                        "run_llm": False,
                    },
                )
            ]
        if decision.kind == DecisionKinds.FORCE_STAGE_TRANSITION:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="append_context_frame",
                    payload={
                        "frame": "LLMMessagesAppendFrame",
                        "messages": [
                            {
                                "role": "system",
                                "content": f"Conversation stage is now: {decision.payload['stage']}",
                            }
                        ],
                    },
                )
            ]
        if decision.kind == DecisionKinds.REQUEST_AVAILABILITY_WINDOW:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="append_context_frame",
                    payload={
                        "frame": "LLMMessagesAppendFrame",
                        "messages": [{"role": "system", "content": str(decision.payload)}],
                    },
                )
            ]
        if decision.kind == DecisionKinds.BLOCK_DELIVERY_UNTIL_CONSENT:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="block_function_call",
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
