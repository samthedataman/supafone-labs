from __future__ import annotations

from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import DecisionKinds, ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState


class VapiAdapter(BaseAdapter):
    provider_name = "vapi"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_hidden_instruction_injection=True,
            supports_mid_call_prompt_patch=True,
            supports_stageful_session_updates=True,
            supports_tool_call_interception=True,
            supports_server_side_transcript_stream=True,
            supports_native_recording=True,
            supports_native_webhooks=True,
            supports_realtime_bidirectional_ws=False,
            supports_post_call_artifact_fetch=True,
        )

    def _session_id(self, raw_event: dict) -> str:
        # Vapi server messages carry the call object at message.call (docs) —
        # accept a sibling `call` too, plus the flat legacy keys.
        msg = raw_event.get("message") if isinstance(raw_event.get("message"), dict) else raw_event
        for source in (raw_event, msg):
            call = source.get("call") if isinstance(source.get("call"), dict) else {}
            if call.get("id"):
                return str(call["id"])
        return str(raw_event.get("session_id") or raw_event.get("call_id") or "session")

    async def parse_event(self, raw_event: dict) -> list:
        # Real Vapi webhooks nest the payload under a top-level "message" key
        # ({"message": {"type": ...}}); accept both nested and flat shapes.
        msg = raw_event.get("message") if isinstance(raw_event.get("message"), dict) else raw_event
        message_type = str(msg.get("type") or "").strip().lower()
        session_id = self._session_id(raw_event)
        provider_session_id = self._provider_session_id(raw_event)

        if message_type in {"call-start", "session-start"}:
            return [
                make_event(
                    EventTypes.SESSION_STARTED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        if message_type == "status-update":
            status = str(msg.get("status") or "").strip().lower()
            if status == "in-progress":
                return [
                    make_event(
                        EventTypes.SESSION_STARTED,
                        session_id=session_id,
                        provider=self.provider_name,
                        provider_session_id=provider_session_id,
                        data=raw_event,
                    )
                ]
            if status == "ended":
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
        if message_type in {"transcript", "message"}:
            role = str(msg.get("role") or "").lower()
            # Real transcripts use transcriptType partial|final; legacy used final=bool.
            transcript_type = str(msg.get("transcriptType") or "").strip().lower()
            final = transcript_type != "partial" if transcript_type else bool(msg.get("final", True))
            if role == "user":
                mapped = EventTypes.CALLER_TRANSCRIPT_FINAL if final else EventTypes.CALLER_TRANSCRIPT_PARTIAL
            else:
                mapped = EventTypes.AGENT_TRANSCRIPT_FINAL if final else EventTypes.AGENT_TRANSCRIPT_PARTIAL
            return [
                make_event(
                    mapped,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="caller" if role == "user" else "agent",
                    text=str(msg.get("transcript") or msg.get("text") or ""),
                    data=raw_event,
                )
            ]
        if message_type == "tool-calls":
            tool_calls = msg.get("toolCallList")
            events = []
            for call in tool_calls if isinstance(tool_calls, list) else []:
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
        if message_type == "function-call":  # legacy shape, kept for compatibility
            return [
                make_event(
                    EventTypes.TOOL_CALLED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    actor="tool",
                    data={"tool_name": msg.get("name"), **msg},
                )
            ]
        if message_type == "function-result":  # legacy shape, kept for compatibility
            payload = dict(msg.get("result") or {})
            payload["tool_name"] = msg.get("name")
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
        if message_type == "end-of-call-report":
            events = [
                make_event(
                    EventTypes.TRANSCRIPT_AVAILABLE,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
            artifact = msg.get("artifact") if isinstance(msg.get("artifact"), dict) else {}
            recording = artifact.get("recording") if isinstance(artifact.get("recording"), dict) else {}
            url = recording.get("url") or artifact.get("recordingUrl")
            if url:
                events.append(
                    make_event(
                        EventTypes.RECORDING_AVAILABLE,
                        session_id=session_id,
                        provider=self.provider_name,
                        provider_session_id=provider_session_id,
                        data={"recording_url": url},
                    )
                )
            events.append(
                make_event(
                    EventTypes.SESSION_ENDED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            )
            return events
        if message_type == "call-end":  # legacy shape, kept for compatibility
            return [
                make_event(
                    EventTypes.SESSION_ENDED,
                    session_id=session_id,
                    provider=self.provider_name,
                    provider_session_id=provider_session_id,
                    data=raw_event,
                )
            ]
        # speech-update / conversation-update / hang are timing chatter.
        return []

    async def compile(
        self,
        decision: RuntimeDecision,
        state: RuntimeState,
    ) -> list[ProviderAction]:
        if decision.kind == DecisionKinds.INJECT_HIDDEN_INSTRUCTION:
            # Vapi Live Call Control "add-message" with triggerResponseEnabled
            # False: the system turn lands in context silently and is NOT spoken
            # or forced into an immediate reply (an assistant_override without a
            # silence flag would be voiced back to the caller).
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="control_add_message",
                    payload={
                        "type": "add-message",
                        "message": {"role": "system", "content": decision.payload["text"]},
                        "triggerResponseEnabled": False,
                    },
                )
            ]
        if decision.kind == DecisionKinds.FORCE_STAGE_TRANSITION:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="assistant_metadata_patch",
                    payload={"stage": decision.payload["stage"]},
                )
            ]
        if decision.kind == DecisionKinds.REQUEST_AVAILABILITY_WINDOW:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="assistant_metadata_patch",
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
        if decision.kind == DecisionKinds.REQUEST_FIELD_REPAIR:
            return [
                ProviderAction(
                    provider=self.provider_name,
                    kind="assistant_override",
                    payload={"instruction": decision.payload["message"]},
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
