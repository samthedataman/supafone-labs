"""Audited mid-call injection contracts for the public runtime matrix.

These records deliberately separate native provider messages from framework
context mutation and from providers that require a cooperative agent hook.
Tests use this registry as the release gate for the fourteen runtimes exposed
by the Supafone Labs console.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

InjectionMode = Literal[
    "native_message",
    "framework_context",
    "custom_llm_context",
    "requires_agent_hook",
    "tap_only",
]
ProbeKind = Literal[
    "managed",
    "active_call",
    "realtime_socket",
    "provider_sdk",
    "framework_local",
    "not_applicable",
]


@dataclass(frozen=True, slots=True)
class ProviderInjectionContract:
    provider_id: str
    display_name: str
    adapter_id: str
    injection_mode: InjectionMode
    action_kind: str | None
    native_message: str | None
    acknowledgement: str
    official_docs: str
    verified_on: str
    live_probe: ProbeKind
    notes: str = ""

    @property
    def injectable(self) -> bool:
        return self.action_kind is not None


PROVIDER_INJECTION_CONTRACTS: tuple[ProviderInjectionContract, ...] = (
    ProviderInjectionContract(
        "supafone",
        "Supafone Agent Factory",
        "supafone",
        "native_message",
        "inject_message",
        "user_text_message",
        "Ultravox data-message REST returns HTTP 204 or the live socket remains healthy.",
        "https://docs.ultravox.ai/agents/guiding-agents",
        "2026-07-12",
        "managed",
        "The managed runtime currently uses Supafone's Ultravox transport adapter.",
    ),
    ProviderInjectionContract(
        "ultravox",
        "Ultravox",
        "ultravox",
        "native_message",
        "inject_message",
        "user_text_message",
        "Send Data Message returns HTTP 204; deferred guidance uses urgency=later.",
        "https://docs.ultravox.ai/agents/guiding-agents",
        "2026-07-12",
        "active_call",
    ),
    ProviderInjectionContract(
        "vapi",
        "Vapi",
        "vapi",
        "native_message",
        "control_add_message",
        "add-message",
        "POST to the live call controlUrl succeeds and the system message enters model context.",
        "https://docs.vapi.ai/calls/call-features",
        "2026-07-12",
        "active_call",
    ),
    ProviderInjectionContract(
        "retell",
        "Retell",
        "retell",
        "custom_llm_context",
        "llm_context_inject",
        "system context entry",
        "The custom-LLM context includes the entry before the next response event is emitted.",
        "https://docs.retellai.com/api-references/llm-websocket",
        "2026-07-12",
        "framework_local",
        "Retell has no provider-side hidden-message event; the custom LLM server owns context.",
    ),
    ProviderInjectionContract(
        "bland",
        "Bland",
        "bland",
        "tap_only",
        None,
        None,
        "Not applicable: current public APIs expose observation and call control, not prompt injection.",
        "https://docs.bland.ai/api-v1/get/active",
        "2026-07-12",
        "not_applicable",
    ),
    ProviderInjectionContract(
        "gpt_realtime",
        "OpenAI Realtime",
        "gpt_realtime",
        "native_message",
        "conversation_item_create",
        "conversation.item.create",
        "Server emits conversation.item.created/done or an error tied to the client event.",
        "https://developers.openai.com/api/reference/resources/realtime",
        "2026-07-12",
        "realtime_socket",
    ),
    ProviderInjectionContract(
        "grok",
        "Grok Voice Agent",
        "grok",
        "native_message",
        "response_create",
        "response.create.instructions",
        "Server emits response.created followed by response.done, or an error.",
        "https://docs.x.ai/developers/model-capabilities/audio/voice-agent",
        "2026-07-12",
        "realtime_socket",
    ),
    ProviderInjectionContract(
        "gemini_live",
        "Gemini Live",
        "gemini_live",
        "native_message",
        "client_content",
        "clientContent user turn",
        "The user-role control turn is accepted; subsequent serverContent reflects the updated instruction.",
        "https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/live-api/start-manage-session",
        "2026-07-12",
        "realtime_socket",
        "Gemini Live rejects system-role clientContent mid-session, so control updates use a user-role turn.",
    ),
    ProviderInjectionContract(
        "elevenlabs",
        "ElevenLabs Agents",
        "elevenlabs",
        "native_message",
        "contextual_update",
        "contextual_update",
        "No direct ack is defined; the socket must remain healthy and the next turn must complete.",
        "https://elevenlabs.io/docs/eleven-agents/libraries/web-sockets",
        "2026-07-12",
        "realtime_socket",
    ),
    ProviderInjectionContract(
        "deepgram",
        "Deepgram Voice Agent",
        "deepgram",
        "native_message",
        "update_prompt",
        "UpdatePrompt",
        "Server emits PromptUpdated; malformed updates emit Error or Warning.",
        "https://developers.deepgram.com/docs/voice-agent-update-prompt",
        "2026-07-12",
        "realtime_socket",
    ),
    ProviderInjectionContract(
        "livekit",
        "LiveKit Agents",
        "livekit",
        "framework_context",
        "chat_context_append",
        "ChatContext.add_message",
        "Agent.update_chat_ctx completes and the persisted context contains the system entry.",
        "https://docs.livekit.io/agents/logic/chat-context/",
        "2026-07-12",
        "framework_local",
    ),
    ProviderInjectionContract(
        "pipecat",
        "Pipecat",
        "pipecat",
        "framework_context",
        "append_context_frame",
        "LLMMessagesAppendFrame",
        "The context aggregator consumes the frame and retains the developer message.",
        "https://docs.pipecat.ai/pipecat/learn/context-management",
        "2026-07-12",
        "framework_local",
    ),
    ProviderInjectionContract(
        "cartesia",
        "Cartesia Line",
        "cartesia",
        "requires_agent_hook",
        None,
        "custom event",
        "Default adapter remains tap-only; a Line agent must explicitly handle UserCustomSent.",
        "https://docs.cartesia.ai/line/sdk/events",
        "2026-07-12",
        "not_applicable",
        "A custom metadata event is transport, not a universal prompt-injection guarantee.",
    ),
    ProviderInjectionContract(
        "inworld",
        "Inworld Realtime",
        "inworld",
        "native_message",
        "conversation_item_create",
        "conversation.item.create",
        "Server emits conversation.item.added/done or an error.",
        "https://dev.docs.inworld.ai/api-reference/realtimeAPI/realtime/realtime-webrtc",
        "2026-07-12",
        "realtime_socket",
    ),
)

CONTRACT_BY_PROVIDER = {
    contract.provider_id: contract for contract in PROVIDER_INJECTION_CONTRACTS
}
