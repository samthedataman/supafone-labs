"""Inworld adapter — TTS component / character-engine events, tap-only.

Inworld's TTS is a speech engine (nothing to coach); its character runtime
emits interaction packets with a ``text`` body and ``routing`` metadata whose
``source.isPlayer`` flag distinguishes the human from the character. Both
shapes are mapped to canonical transcript events so the oracle can observe an
Inworld-powered stack; ``compile`` returns no actions (tap-only).
"""
from __future__ import annotations

from typing import Any

from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent, EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState


class InworldAdapter(BaseAdapter):
    provider_name = "inworld"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_hidden_instruction_injection=False,
            supports_mid_call_prompt_patch=False,
            supports_stageful_session_updates=False,
            supports_tool_call_interception=False,
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

    async def parse_event(self, raw_event: dict[str, Any]) -> list[CanonicalEvent]:
        event_type = str(raw_event.get("type") or "").strip().lower()
        session_id = self._session_id(raw_event)
        provider_session_id = self._provider_session_id(raw_event) or str(
            raw_event.get("interaction_id") or raw_event.get("interactionId") or ""
        )

        if event_type in {"session_start", "session.started", "control_session_start"}:
            return [
                make_event(
                    EventTypes.SESSION_STARTED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
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
            if caller:
                mapped = (
                    EventTypes.CALLER_TRANSCRIPT_FINAL if final else EventTypes.CALLER_TRANSCRIPT_PARTIAL
                )
            else:
                mapped = (
                    EventTypes.AGENT_TRANSCRIPT_FINAL if final else EventTypes.AGENT_TRANSCRIPT_PARTIAL
                )
            return [
                make_event(
                    mapped,
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
        # Tap-only: a speech engine has no instruction channel.
        return []
