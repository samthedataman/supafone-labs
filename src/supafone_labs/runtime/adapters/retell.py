"""Retell adapter — custom-LLM websocket turns + agent-level webhook events.

Retell runs the voice loop (STT -> your LLM -> TTS). Two raw shapes reach us:

* **Custom-LLM websocket** messages keyed by ``interaction_type``
  (``call_details``, ``update_only``, ``response_required``,
  ``reminder_required``) carrying a rolling ``transcript`` array of
  ``{"role": "agent"|"user", "content": ...}`` utterances.
* **Webhook** envelopes keyed by ``event`` (``call_started``, ``call_ended``,
  ``call_analyzed``) carrying a ``call`` object.

Injection: Retell's custom-LLM loop lets us prepend context to the model on the
next ``response_required`` turn, so a hidden instruction compiles to an
``llm_context_inject`` action carrying a system-role message.
"""
from __future__ import annotations

from typing import Any

from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import DecisionKinds, ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent, EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState


class RetellAdapter(BaseAdapter):
    provider_name = "retell"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_hidden_instruction_injection=True,
            supports_mid_call_prompt_patch=True,
            supports_stageful_session_updates=False,
            supports_tool_call_interception=True,
            supports_server_side_transcript_stream=True,
            supports_native_recording=True,
            supports_native_webhooks=True,
            supports_realtime_bidirectional_ws=True,
            supports_post_call_artifact_fetch=True,
        )

    def _session_id(self, raw_event: dict[str, Any]) -> str:
        call = raw_event.get("call") if isinstance(raw_event.get("call"), dict) else {}
        return str(
            raw_event.get("session_id")
            or raw_event.get("call_id")
            or call.get("call_id")
            or "session"
        )

    def _transcript_events(
        self, raw_event: dict[str, Any], session_id: str, provider_session_id: str
    ) -> list[CanonicalEvent]:
        transcript = raw_event.get("transcript")
        if not isinstance(transcript, list) or not transcript:
            return []
        # Only the newest utterance is fresh — earlier turns were already ingested.
        last = transcript[-1]
        if not isinstance(last, dict):
            return []
        role = str(last.get("role") or "").strip().lower()
        text = str(last.get("content") or "")
        caller = role in {"user", "caller"}
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

    async def parse_event(self, raw_event: dict[str, Any]) -> list[CanonicalEvent]:
        session_id = self._session_id(raw_event)
        provider_session_id = self._provider_session_id(raw_event) or str(
            raw_event.get("call_id") or ""
        )

        interaction = str(raw_event.get("interaction_type") or "").strip().lower()
        if interaction == "call_details":
            return [
                make_event(
                    EventTypes.SESSION_STARTED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if interaction in {"update_only", "response_required", "reminder_required"}:
            return self._transcript_events(raw_event, session_id, provider_session_id)
        if interaction == "ping_pong":
            return []

        webhook = str(raw_event.get("event") or "").strip().lower()
        if webhook == "call_started":
            return [
                make_event(
                    EventTypes.SESSION_STARTED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if webhook == "call_ended":
            return [
                make_event(
                    EventTypes.SESSION_ENDED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if webhook == "call_analyzed":
            call = raw_event.get("call") if isinstance(raw_event.get("call"), dict) else {}
            events = [
                make_event(
                    EventTypes.TRANSCRIPT_AVAILABLE,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
            if call.get("recording_url"):
                events.append(
                    make_event(
                        EventTypes.RECORDING_AVAILABLE,
                        session_id=session_id,
                        provider=self.provider_name,
                        provider_session_id=provider_session_id,
                        data={"recording_url": call.get("recording_url")},
                    )
                )
            return events
        return []

    async def compile(
        self,
        decision: RuntimeDecision,
        state: RuntimeState,
    ) -> list[ProviderAction]:
        if decision.kind == DecisionKinds.INJECT_HIDDEN_INSTRUCTION:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="llm_context_inject",
                    payload={"role": "system", "content": decision.payload["text"]},
                )
            ]
        if decision.kind == DecisionKinds.REQUEST_FIELD_REPAIR:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="llm_context_inject",
                    payload={"role": "system", "content": decision.payload["message"]},
                )
            ]
        if decision.kind == DecisionKinds.FORCE_STAGE_TRANSITION:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="update_dynamic_variables",
                    payload={"stage": decision.payload["stage"]},
                )
            ]
        if decision.kind == DecisionKinds.REQUEST_AVAILABILITY_WINDOW:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="update_dynamic_variables",
                    payload=decision.payload,
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
