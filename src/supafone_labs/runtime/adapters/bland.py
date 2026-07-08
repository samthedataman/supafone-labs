"""Bland adapter — end-of-call webhook + live webhook_events stream, tap-only.

What Bland actually ships (per current docs):

* **End-of-call webhook** (the ``webhook`` param on Send Call): one POST when
  the call ends, carrying ``call_id``, ``completed``, ``summary``,
  ``concatenated_transcript``, ``recording_url`` and a ``transcripts`` array of
  ``{"id", "user": "user"|"assistant"|"robot"|"agent-action", "text", ...}``.
* **Live events** (the ``webhook_events`` param): mid-call event lines shaped
  ``{"level", "category", "message", "call_id", "timestamp"}`` where
  ``category: "call"`` messages carry live speech as ``"Agent speech: ..."`` /
  ``"Handling user speech: ..."``.

Bland documents NO mid-call injection or prompt-update API (only stop/transfer),
so this adapter is **tap-only**: ``compile`` returns no actions and the
capabilities say so. Legacy ``call_started``/``utterance``/``tool_call`` shapes
are still parsed for backward compatibility with pre-0.2 fixtures.
"""
from __future__ import annotations

from typing import Any

from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent, EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState

_AGENT_SPEECH_PREFIX = "agent speech:"
_USER_SPEECH_PREFIX = "handling user speech:"


class BlandAdapter(BaseAdapter):
    provider_name = "bland"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_hidden_instruction_injection=False,
            supports_mid_call_prompt_patch=False,  # no documented mid-call control API
            supports_stageful_session_updates=False,
            supports_tool_call_interception=False,
            supports_server_side_transcript_stream=True,  # webhook_events speech lines
            supports_native_recording=True,
            supports_native_webhooks=True,
            supports_realtime_bidirectional_ws=False,
            supports_post_call_artifact_fetch=True,
        )

    def _end_of_call_events(
        self, raw_event: dict[str, Any], session_id: str, provider_session_id: str
    ) -> list[CanonicalEvent]:
        events: list[CanonicalEvent] = []
        transcripts = raw_event.get("transcripts")
        for turn in transcripts if isinstance(transcripts, list) else []:
            if not isinstance(turn, dict):
                continue
            text = str(turn.get("text") or "")
            if not text:
                continue
            speaker = str(turn.get("user") or "").strip().lower()
            caller = speaker == "user"
            events.append(
                make_event(
                    EventTypes.CALLER_TRANSCRIPT_FINAL if caller else EventTypes.AGENT_TRANSCRIPT_FINAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="caller" if caller else "agent",
                    text=text,
                    data=turn,
                )
            )
        events.append(
            make_event(
                EventTypes.TRANSCRIPT_AVAILABLE,
                session_id=session_id,
                provider=self.provider_name,
                provider_session_id=provider_session_id,
                data={"summary": raw_event.get("summary"), "concatenated_transcript": raw_event.get("concatenated_transcript")},
            )
        )
        if raw_event.get("recording_url"):
            events.append(
                make_event(
                    EventTypes.RECORDING_AVAILABLE,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data={"recording_url": raw_event.get("recording_url")},
                )
            )
        events.append(
            make_event(
                EventTypes.SESSION_ENDED,
                session_id=session_id,
                provider=self.provider_name,
                provider_session_id=provider_session_id,
                data={"completed": raw_event.get("completed"), "status": raw_event.get("status")},
            )
        )
        return events

    def _live_event(
        self, raw_event: dict[str, Any], session_id: str, provider_session_id: str
    ) -> list[CanonicalEvent]:
        message = str(raw_event.get("message") or "")
        lowered = message.strip().lower()
        if lowered.startswith(_AGENT_SPEECH_PREFIX):
            text = message.strip()[len(_AGENT_SPEECH_PREFIX):].strip()
            mapped, actor = EventTypes.AGENT_TRANSCRIPT_FINAL, "agent"
        elif lowered.startswith(_USER_SPEECH_PREFIX):
            text = message.strip()[len(_USER_SPEECH_PREFIX):].strip()
            mapped, actor = EventTypes.CALLER_TRANSCRIPT_FINAL, "caller"
        else:
            return []
        if not text:
            return []
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

    async def parse_event(self, raw_event: dict[str, Any]) -> list[CanonicalEvent]:
        event_type = str(raw_event.get("type") or "").strip().lower()
        session_id = self._session_id(raw_event)
        provider_session_id = self._provider_session_id(raw_event)

        # Real live webhook_events line ({"category": "call", "message": ...}).
        if not event_type and str(raw_event.get("category") or "").strip().lower() == "call":
            return self._live_event(raw_event, session_id, provider_session_id)

        # Real end-of-call webhook: no "type" field; recognized by transcripts/completed.
        if not event_type and ("transcripts" in raw_event or "concatenated_transcript" in raw_event):
            return self._end_of_call_events(raw_event, session_id, provider_session_id)

        # --- legacy shapes, kept for backward compatibility ---
        if event_type in {"call_started", "conversation_started"}:
            return [
                make_event(
                    EventTypes.SESSION_STARTED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if event_type == "utterance":
            speaker = str(raw_event.get("speaker") or "").lower()
            caller = speaker in {"caller", "user"}
            return [
                make_event(
                    EventTypes.CALLER_TRANSCRIPT_FINAL if caller else EventTypes.AGENT_TRANSCRIPT_FINAL,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="caller" if caller else "agent",
                    text=str(raw_event.get("text") or ""),
                    data=raw_event,
                )
            ]
        if event_type == "pathway.transition":
            return [
                make_event(
                    EventTypes.STAGE_TRANSITION,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data={"stage": raw_event.get("pathway")},
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
                    data={"tool_name": raw_event.get("tool"), **raw_event},
                )
            ]
        if event_type == "tool_result":
            payload = dict(raw_event.get("payload") or {})
            payload["tool_name"] = raw_event.get("tool")
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
        if event_type == "recording":
            return [
                make_event(
                    EventTypes.RECORDING_AVAILABLE,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data={"recording_url": raw_event.get("url")},
                )
            ]
        if event_type == "call_ended":
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
        # Tap-only: Bland exposes no documented way to inject instructions,
        # patch the prompt, or speak text into an active call. Pretending
        # otherwise (the old set_workflow_variable action) was dishonest.
        return []
