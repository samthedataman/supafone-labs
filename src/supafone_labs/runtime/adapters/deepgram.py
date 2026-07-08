"""Deepgram adapter — Voice Agent events AND raw streaming-STT Results.

Deepgram shows up in two very different roles, and this adapter handles both:

* **Voice Agent API** (``wss://agent.deepgram.com/v1/agent/converse``) — a full
  agent. Typed messages: ``Welcome``, ``SettingsApplied``, ``ConversationText``
  (``role``: ``user``/``assistant``), ``UserStartedSpeaking``, ``AgentThinking``,
  ``AgentStartedSpeaking``, ``AgentAudioDone``, ``FunctionCallRequest`` /
  ``FunctionCallResponse``, ``Error``. Injection is first-class:
  ``InjectAgentMessage`` (speak now) and ``UpdatePrompt`` (silent instruction
  patch) — SupafoneLabs compiles hidden instructions to ``UpdatePrompt`` so the
  whisper is read, not spoken.

* **Streaming STT** (``wss://api.deepgram.com/v1/listen``) — a pipeline
  component, tap-only. ``Results`` messages carry
  ``channel.alternatives[0].transcript`` with ``is_final`` / ``speech_final``
  and optional ``languages``. There is no role in raw STT: callers tag frames
  with ``speaker``/``track`` (the same convention as the production Twilio
  fork -> Deepgram tap), defaulting to the caller.
"""
from __future__ import annotations

from typing import Any

from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import DecisionKinds, ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent, EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState

_CALLER_SPEAKERS = {"caller", "user", "client", "inbound", "inbound_track"}


class DeepgramAdapter(BaseAdapter):
    provider_name = "deepgram"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_hidden_instruction_injection=True,   # UpdatePrompt / InjectAgentMessage
            supports_mid_call_prompt_patch=True,          # UpdatePrompt
            supports_stageful_session_updates=False,
            supports_tool_call_interception=True,         # FunctionCallRequest round-trip
            supports_server_side_transcript_stream=True,  # ConversationText + listen Results
            supports_native_recording=False,
            supports_native_webhooks=False,
            supports_realtime_bidirectional_ws=True,
            supports_post_call_artifact_fetch=False,
        )

    def _stt_language(self, raw_event: dict[str, Any]) -> str:
        # Prerecorded responses put `languages` top-level; live streaming
        # (nova-3 language=multi) nests it at alternatives[0].languages —
        # both verified against the real API.
        languages = raw_event.get("languages")
        if isinstance(languages, list) and languages:
            return str(languages[0] or "")
        channel = raw_event.get("channel") if isinstance(raw_event.get("channel"), dict) else {}
        alternatives = channel.get("alternatives") if isinstance(channel, dict) else []
        alt = alternatives[0] if isinstance(alternatives, list) and alternatives else {}
        if isinstance(alt, dict):
            alt_languages = alt.get("languages")
            if isinstance(alt_languages, list) and alt_languages:
                return str(alt_languages[0] or "")
            return str(alt.get("language") or alt.get("detected_language") or "")
        return ""

    def _parse_stt_results(
        self, raw_event: dict[str, Any], session_id: str, provider_session_id: str
    ) -> list[CanonicalEvent]:
        channel = raw_event.get("channel") if isinstance(raw_event.get("channel"), dict) else {}
        alternatives = channel.get("alternatives") if isinstance(channel, dict) else []
        alt = alternatives[0] if isinstance(alternatives, list) and alternatives else {}
        text = str((alt or {}).get("transcript") or "").strip()
        if not text:
            return []
        speaker = str(raw_event.get("speaker") or raw_event.get("track") or "caller").lower()
        caller = speaker in _CALLER_SPEAKERS
        final = bool(raw_event.get("is_final") or raw_event.get("speech_final"))
        if caller:
            mapped = EventTypes.CALLER_TRANSCRIPT_FINAL if final else EventTypes.CALLER_TRANSCRIPT_PARTIAL
        else:
            mapped = EventTypes.AGENT_TRANSCRIPT_FINAL if final else EventTypes.AGENT_TRANSCRIPT_PARTIAL
        data = dict(raw_event)
        language = self._stt_language(raw_event)
        if language:
            data["language"] = language
        return [
            make_event(
                mapped,
                session_id=session_id,
                provider=self.provider_name,
                provider_session_id=provider_session_id,
                actor="caller" if caller else "agent",
                text=text,
                data=data,
            )
        ]

    async def parse_event(self, raw_event: dict[str, Any]) -> list[CanonicalEvent]:
        event_type = str(raw_event.get("type") or "").strip()
        session_id = self._session_id(raw_event)
        provider_session_id = self._provider_session_id(raw_event) or str(
            raw_event.get("request_id") or ""
        )

        # --- Voice Agent API (typed PascalCase messages) ---
        if event_type in {"Welcome", "SettingsApplied"}:
            return [
                make_event(
                    EventTypes.SESSION_STARTED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if event_type == "ConversationText":
            role = str(raw_event.get("role") or "").lower()
            caller = role in {"user", "caller"}
            return [
                make_event(
                    EventTypes.CALLER_TRANSCRIPT_FINAL if caller else EventTypes.AGENT_TRANSCRIPT_FINAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="caller" if caller else "agent",
                    text=str(raw_event.get("content") or ""),
                    data=raw_event,
                )
            ]
        if event_type == "FunctionCallRequest":
            functions = raw_event.get("functions")
            fn = functions[0] if isinstance(functions, list) and functions else raw_event
            return [
                make_event(
                    EventTypes.TOOL_CALLED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="tool",
                    data={"tool_name": (fn or {}).get("name"), **raw_event},
                )
            ]
        if event_type == "FunctionCallResponse":
            return [
                make_event(
                    EventTypes.TOOL_RESULT,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="tool",
                    data={
                        "tool_name": raw_event.get("name"),
                        "result": raw_event.get("content"),
                        **raw_event,
                    },
                )
            ]
        if event_type in {"PromptUpdated", "SpeakUpdated"}:
            return [
                make_event(
                    EventTypes.SESSION_UPDATED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if event_type == "InjectionRefused":
            return [
                make_event(
                    EventTypes.PROVIDER_ERROR,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data={"refused": True, **raw_event},
                )
            ]
        if event_type == "Error":
            return [
                make_event(
                    EventTypes.PROVIDER_ERROR,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if event_type == "Close" or event_type == "CloseConnection":
            return [
                make_event(
                    EventTypes.SESSION_ENDED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]

        # --- Streaming STT (listen) Results ---
        if event_type == "Results" or (not event_type and "channel" in raw_event):
            return self._parse_stt_results(raw_event, session_id, provider_session_id)
        # UserStartedSpeaking / AgentThinking / AgentAudioDone / Metadata /
        # UtteranceEnd are timing signals, not conversational state.
        return []

    async def compile(
        self,
        decision: RuntimeDecision,
        state: RuntimeState,
    ) -> list[ProviderAction]:
        # Docs-verified message shapes: UpdatePrompt carries "prompt" (and adds
        # to, not replaces, the live prompt); InjectAgentMessage carries
        # "message" (+ optional behavior: default|queue).
        if decision.kind == DecisionKinds.INJECT_HIDDEN_INSTRUCTION:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="update_prompt",
                    payload={"type": "UpdatePrompt", "prompt": decision.payload["text"]},
                )
            ]
        if decision.kind == DecisionKinds.REQUEST_FIELD_REPAIR:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="inject_agent_message",
                    payload={
                        "type": "InjectAgentMessage",
                        "message": decision.payload["message"],
                        "behavior": "queue",
                    },
                )
            ]
        if decision.kind == DecisionKinds.FORCE_STAGE_TRANSITION:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="update_prompt",
                    payload={
                        "type": "UpdatePrompt",
                        "prompt": f"Conversation stage is now: {decision.payload['stage']}",
                    },
                )
            ]
        if decision.kind == DecisionKinds.REQUEST_AVAILABILITY_WINDOW:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="update_prompt",
                    payload={"type": "UpdatePrompt", "prompt": str(decision.payload)},
                )
            ]
        if decision.kind == DecisionKinds.BLOCK_DELIVERY_UNTIL_CONSENT:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="deny_function_call",
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
