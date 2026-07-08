"""Cartesia adapter — TTS/STT *component*, tap-only.

Cartesia is not an agent: Sonic is a TTS engine and Ink is a streaming STT
engine. There is no model to whisper to, so this adapter is **tap-only** —
Ink websocket messages (``type: "transcript"`` with ``text`` / ``is_final`` /
``language``, plus ``flush_done`` / ``done`` / ``error``) become canonical
transcript events that feed the oracle watching the rest of your stack.
``compile`` intentionally returns no actions; capabilities advertise that.
"""
from __future__ import annotations

from typing import Any

from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent, EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState

_CALLER_SPEAKERS = {"caller", "user", "client", "inbound", "inbound_track"}


class CartesiaAdapter(BaseAdapter):
    provider_name = "cartesia"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_hidden_instruction_injection=False,
            supports_mid_call_prompt_patch=False,
            supports_stageful_session_updates=False,
            supports_tool_call_interception=False,
            supports_server_side_transcript_stream=True,  # Ink STT
            supports_native_recording=False,
            supports_native_webhooks=False,
            supports_realtime_bidirectional_ws=True,
            supports_post_call_artifact_fetch=False,
        )

    async def parse_event(self, raw_event: dict[str, Any]) -> list[CanonicalEvent]:
        event_type = str(raw_event.get("type") or "").strip().lower()
        session_id = self._session_id(raw_event)
        provider_session_id = self._provider_session_id(raw_event) or str(
            raw_event.get("context_id") or raw_event.get("request_id") or ""
        )

        if event_type == "transcript":
            text = str(raw_event.get("text") or "").strip()
            if not text:
                return []
            speaker = str(raw_event.get("speaker") or raw_event.get("track") or "caller").lower()
            caller = speaker in _CALLER_SPEAKERS
            final = bool(raw_event.get("is_final", False))
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
        if event_type == "done":
            return [
                make_event(
                    EventTypes.SESSION_ENDED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        # flush_done and audio chunks are transport chatter.
        return []

    async def compile(
        self,
        decision: RuntimeDecision,
        state: RuntimeState,
    ) -> list[ProviderAction]:
        # Tap-only: a raw TTS/STT engine has no agent to coach. The oracle's
        # directive still reaches whatever *agent* adapter shares the session.
        return []
