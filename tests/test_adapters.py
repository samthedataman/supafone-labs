"""Every provider adapter, one contract: representative native payloads must
parse into canonical events, and an inject decision must compile into that
provider's native control (or nothing, for tap-only speech components)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import pytest

from supafone_labs.runtime.adapters import (
    BlandAdapter,
    CartesiaAdapter,
    DeepgramAdapter,
    ElevenLabsAdapter,
    GenericWebhookAdapter,
    GPTRealtimeAdapter,
    GrokAdapter,
    InworldAdapter,
    LivekitAdapter,
    PipecatAdapter,
    RetellAdapter,
    UltravoxAdapter,
    VapiAdapter,
)
from supafone_labs.runtime.core.decision import RuntimeDecision
from supafone_labs.runtime.core.events import EventTypes
from supafone_labs.runtime.core.state import apply_events, build_initial_state

CALLER_TEXT = "I was rear-ended at a red light yesterday and my neck hurts."
AGENT_TEXT = "I'm so sorry to hear that. Are you safe right now?"


@dataclass
class ProviderCase:
    adapter: Any
    start: Optional[dict] = None
    caller: Optional[dict] = None
    agent: Optional[dict] = None
    tool_call: Optional[dict] = None
    end: Optional[dict] = None
    inject_kind: Optional[str] = None  # None => tap-only (no injection channel)
    extra_caller_shapes: list[dict] = field(default_factory=list)


CASES: dict[str, ProviderCase] = {
    "ultravox": ProviderCase(
        adapter=UltravoxAdapter(),
        start={"type": "call.started", "call_id": "c1"},
        caller={"type": "transcript", "speaker": "caller", "text": CALLER_TEXT, "final": True, "call_id": "c1"},
        agent={"type": "transcript", "speaker": "agent", "text": AGENT_TEXT, "final": True, "call_id": "c1"},
        tool_call={"type": "tool_call", "name": "book_appointment", "call_id": "c1"},
        end={"type": "call.ended", "call_id": "c1"},
        inject_kind="inject_message",
    ),
    # Doc-verified shape: everything nests under a top-level "message" key,
    # transcripts use transcriptType partial|final with the text in "transcript",
    # tool calls are type "tool-calls" with toolCallList.
    "vapi": ProviderCase(
        adapter=VapiAdapter(),
        start={"message": {"type": "status-update", "status": "in-progress"}, "call": {"id": "c2"}},
        caller={
            "message": {
                "type": "transcript",
                "role": "user",
                "transcriptType": "final",
                "transcript": CALLER_TEXT,
            },
            "call": {"id": "c2"},
        },
        agent={
            "message": {
                "type": "transcript",
                "role": "assistant",
                "transcriptType": "final",
                "transcript": AGENT_TEXT,
            },
            "call": {"id": "c2"},
        },
        tool_call={
            "message": {
                "type": "tool-calls",
                "toolCallList": [{"id": "tc_1", "name": "book_appointment", "arguments": {}}],
            },
            "call": {"id": "c2"},
        },
        end={
            "message": {"type": "end-of-call-report", "endedReason": "hangup"},
            "call": {"id": "c2"},
        },
        inject_kind="assistant_override",
    ),
    # Doc-verified: live speech arrives as webhook_events "call" lines; the
    # end-of-call webhook carries the transcripts array. Bland documents NO
    # mid-call injection API, so the adapter is tap-only.
    "bland": ProviderCase(
        adapter=BlandAdapter(),
        caller={"category": "call", "message": f"Handling user speech: {CALLER_TEXT}", "call_id": "c3"},
        agent={"category": "call", "message": f"Agent speech: {AGENT_TEXT}", "call_id": "c3"},
        end={
            "call_id": "c3",
            "completed": True,
            "concatenated_transcript": f"user: {CALLER_TEXT}",
            "transcripts": [],
        },
        inject_kind=None,  # tap-only: no documented mid-call control
    ),
    "gpt_realtime": ProviderCase(
        adapter=GPTRealtimeAdapter(),
        start={"type": "session.created", "session_id": "c4"},
        caller={
            "type": "conversation.item.created",
            "item": {"role": "user", "text": CALLER_TEXT},
            "session_id": "c4",
        },
        agent={"type": "response.audio_transcript.done", "transcript": AGENT_TEXT, "session_id": "c4"},
        tool_call={
            "type": "response.function_call_arguments.done",
            "name": "book_appointment",
            "session_id": "c4",
        },
        inject_kind="session_update",
    ),
    "retell": ProviderCase(
        adapter=RetellAdapter(),
        start={"interaction_type": "call_details", "call": {"call_id": "c5"}},
        caller={
            "interaction_type": "response_required",
            "call_id": "c5",
            "transcript": [
                {"role": "agent", "content": "Thanks for calling, how can I help?"},
                {"role": "user", "content": CALLER_TEXT},
            ],
        },
        agent={
            "interaction_type": "update_only",
            "call_id": "c5",
            "transcript": [
                {"role": "user", "content": CALLER_TEXT},
                {"role": "agent", "content": AGENT_TEXT},
            ],
        },
        end={"event": "call_ended", "call": {"call_id": "c5"}},
        inject_kind="llm_context_inject",
    ),
    # Doc-verified: xAI's Voice Agent API is OpenAI-compatible but documents no
    # agent-transcript events; both sides' committed turns arrive as
    # conversation.item.created, and caller STT streams via
    # conversation.item.input_audio_transcription.updated (cumulative).
    "grok": ProviderCase(
        adapter=GrokAdapter(),
        start={"type": "conversation.created", "session_id": "c6"},
        caller={
            "type": "conversation.item.created",
            "item": {"role": "user", "text": CALLER_TEXT},
            "session_id": "c6",
        },
        agent={
            "type": "conversation.item.created",
            "item": {"role": "assistant", "text": AGENT_TEXT},
            "session_id": "c6",
        },
        tool_call={
            "type": "response.function_call_arguments.done",
            "name": "book_appointment",
            "session_id": "c6",
        },
        inject_kind="session_update",
    ),
    "elevenlabs": ProviderCase(
        adapter=ElevenLabsAdapter(),
        start={
            "type": "conversation_initiation_metadata",
            "conversation_initiation_metadata_event": {"conversation_id": "conv_1"},
            "session_id": "c7",
        },
        caller={
            "type": "user_transcript",
            "user_transcription_event": {"user_transcript": CALLER_TEXT},
            "session_id": "c7",
        },
        agent={
            "type": "agent_response",
            "agent_response_event": {"agent_response": AGENT_TEXT},
            "session_id": "c7",
        },
        tool_call={
            "type": "client_tool_call",
            "client_tool_call": {"tool_name": "book_appointment", "tool_call_id": "t1"},
            "session_id": "c7",
        },
        end={"type": "post_call_transcription", "session_id": "c7", "data": {}},
        inject_kind="contextual_update",
    ),
    "deepgram": ProviderCase(
        adapter=DeepgramAdapter(),
        start={"type": "Welcome", "request_id": "req_1", "session_id": "c8"},
        caller={"type": "ConversationText", "role": "user", "content": CALLER_TEXT, "session_id": "c8"},
        agent={"type": "ConversationText", "role": "assistant", "content": AGENT_TEXT, "session_id": "c8"},
        tool_call={
            "type": "FunctionCallRequest",
            "functions": [{"id": "f1", "name": "book_appointment", "client_side": True}],
            "session_id": "c8",
        },
        end={"type": "Close", "session_id": "c8"},
        inject_kind="update_prompt",
        extra_caller_shapes=[
            # Raw streaming-STT Results (the exact shape the production
            # Twilio-fork tap consumes from wss://api.deepgram.com/v1/listen).
            {
                "type": "Results",
                "channel": {"alternatives": [{"transcript": CALLER_TEXT, "confidence": 0.99}]},
                "is_final": True,
                "speech_final": True,
                "languages": ["en"],
                "speaker": "caller",
                "session_id": "c8",
            },
        ],
    ),
    "pipecat": ProviderCase(
        adapter=PipecatAdapter(),
        start={"frame": "StartFrame", "session_id": "c9"},
        caller={"frame": "TranscriptionFrame", "text": CALLER_TEXT, "session_id": "c9"},
        agent={"frame": "TTSTextFrame", "text": AGENT_TEXT, "session_id": "c9"},
        tool_call={
            "frame": "FunctionCallInProgressFrame",
            "function_name": "book_appointment",
            "session_id": "c9",
        },
        end={"frame": "EndFrame", "session_id": "c9"},
        inject_kind="append_context_frame",
    ),
    "livekit": ProviderCase(
        adapter=LivekitAdapter(),
        start={"type": "session_started", "room": "room_1", "session_id": "c10"},
        caller={
            "type": "user_input_transcribed",
            "transcript": CALLER_TEXT,
            "is_final": True,
            "session_id": "c10",
        },
        agent={
            "type": "conversation_item_added",
            "item": {"role": "assistant", "text_content": AGENT_TEXT},
            "session_id": "c10",
        },
        tool_call={
            "type": "function_tools_executed",
            "function_calls": [{"name": "book_appointment"}],
            "session_id": "c10",
        },
        end={"type": "close", "session_id": "c10"},
        inject_kind="chat_context_append",
    ),
    "cartesia": ProviderCase(
        adapter=CartesiaAdapter(),
        caller={
            "type": "transcript",
            "text": CALLER_TEXT,
            "is_final": True,
            "request_id": "r1",
            "session_id": "c11",
        },
        agent={
            "type": "transcript",
            "text": AGENT_TEXT,
            "is_final": True,
            "speaker": "agent",
            "session_id": "c11",
        },
        end={"type": "done", "session_id": "c11"},
        inject_kind=None,  # tap-only
    ),
    "inworld": ProviderCase(
        adapter=InworldAdapter(),
        start={"type": "session_start", "session_id": "c12"},
        caller={
            "type": "text",
            "text": {"text": CALLER_TEXT, "final": True},
            "routing": {"source": {"isPlayer": True}},
            "session_id": "c12",
        },
        agent={
            "type": "text",
            "text": {"text": AGENT_TEXT, "final": True},
            "routing": {"source": {"isPlayer": False}},
            "session_id": "c12",
        },
        end={"type": "session_end", "session_id": "c12"},
        inject_kind=None,  # tap-only
    ),
    "generic": ProviderCase(
        adapter=GenericWebhookAdapter(),
        start={"event": "call_started", "session_id": "c13"},
        caller={"type": "message", "role": "user", "text": CALLER_TEXT, "session_id": "c13"},
        agent={"type": "message", "role": "assistant", "text": AGENT_TEXT, "session_id": "c13"},
        tool_call={"type": "tool_call", "tool": "book_appointment", "session_id": "c13"},
        end={"event": "call_ended", "session_id": "c13"},
        inject_kind="inject",
    ),
}

ALL = sorted(CASES)
WITH = lambda field_name: [n for n in ALL if getattr(CASES[n], field_name) is not None]  # noqa: E731


@pytest.mark.parametrize("name", WITH("start"))
async def test_parse_session_start(name):
    case = CASES[name]
    events = await case.adapter.parse_event(case.start)
    assert events, f"{name}: start payload produced no events"
    assert events[0].type == EventTypes.SESSION_STARTED
    assert events[0].provider == case.adapter.provider_name


@pytest.mark.parametrize("name", ALL)
async def test_parse_caller_transcript(name):
    case = CASES[name]
    events = await case.adapter.parse_event(case.caller)
    assert events, f"{name}: caller payload produced no events"
    event = events[0]
    assert event.type == EventTypes.CALLER_TRANSCRIPT_FINAL
    assert event.actor == "caller"
    assert CALLER_TEXT in event.text


@pytest.mark.parametrize("name", ALL)
async def test_parse_agent_transcript(name):
    case = CASES[name]
    events = await case.adapter.parse_event(case.agent)
    assert events, f"{name}: agent payload produced no events"
    event = events[0]
    assert event.type == EventTypes.AGENT_TRANSCRIPT_FINAL
    assert event.actor == "agent"
    assert AGENT_TEXT in event.text


@pytest.mark.parametrize("name", WITH("tool_call"))
async def test_parse_tool_call(name):
    case = CASES[name]
    events = await case.adapter.parse_event(case.tool_call)
    assert events, f"{name}: tool payload produced no events"
    event = events[0]
    assert event.type == EventTypes.TOOL_CALLED
    assert event.data.get("tool_name") == "book_appointment"


@pytest.mark.parametrize("name", WITH("end"))
async def test_parse_session_end(name):
    case = CASES[name]
    events = await case.adapter.parse_event(case.end)
    assert events, f"{name}: end payload produced no events"
    assert any(e.type == EventTypes.SESSION_ENDED for e in events)


@pytest.mark.parametrize("name", ALL)
async def test_compile_hidden_instruction(name):
    case = CASES[name]
    decision = RuntimeDecision.inject_hidden_instruction("Acknowledge the injury before logistics.")
    state = build_initial_state(provider=case.adapter.provider_name, session_id="s1")
    actions = await case.adapter.compile(decision, state)
    if case.inject_kind is None:
        assert actions == [], f"{name} is tap-only but compiled {actions}"
    else:
        assert actions, f"{name}: inject decision compiled to nothing"
        action = actions[0]
        assert action.kind == case.inject_kind
        assert action.provider == case.adapter.provider_name
        assert "Acknowledge the injury" in str(action.payload)


@pytest.mark.parametrize("name", ALL)
def test_capabilities_match_injection_reality(name):
    case = CASES[name]
    caps = case.adapter.capabilities()
    can_whisper = caps.supports_hidden_instruction_injection or caps.supports_mid_call_prompt_patch
    if case.inject_kind is None:
        assert not can_whisper, f"{name} claims injection but compiles nothing"
    else:
        assert can_whisper, f"{name} compiles an injection but claims no channel"


@pytest.mark.parametrize("name", ALL)
async def test_full_conversation_reduces_into_state(name):
    case = CASES[name]
    state = build_initial_state(provider=case.adapter.provider_name, session_id="s1")
    for payload in (case.start, case.caller, case.agent, case.tool_call, case.end):
        if payload is None:
            continue
        events = await case.adapter.parse_event(payload)
        state = apply_events(events, state)
    texts = [t.text for t in state.transcript]
    assert any(CALLER_TEXT in t for t in texts)
    assert any(AGENT_TEXT in t for t in texts)
    assert state.last_caller_text and CALLER_TEXT in state.last_caller_text
    if case.tool_call is not None:
        assert any(r.tool_name == "book_appointment" for r in state.tool_history)


async def test_deepgram_raw_stt_results_shape():
    """The exact wss://api.deepgram.com/v1/listen Results shape (verified live) taps as caller speech."""
    case = CASES["deepgram"]
    for payload in case.extra_caller_shapes:
        events = await case.adapter.parse_event(payload)
        assert events and events[0].type == EventTypes.CALLER_TRANSCRIPT_FINAL
        assert events[0].text == CALLER_TEXT
        assert events[0].data.get("language") == "en"


async def test_deepgram_stt_partial_and_agent_track():
    adapter = DeepgramAdapter()
    partial = {
        "type": "Results",
        "channel": {"alternatives": [{"transcript": "I was rear"}]},
        "is_final": False,
        "session_id": "c8",
    }
    events = await adapter.parse_event(partial)
    assert events and events[0].type == EventTypes.CALLER_TRANSCRIPT_PARTIAL
    agent_track = {
        "type": "Results",
        "channel": {"alternatives": [{"transcript": AGENT_TEXT}]},
        "is_final": True,
        "track": "outbound",
        "session_id": "c8",
    }
    events = await adapter.parse_event(agent_track)
    assert events and events[0].type == EventTypes.AGENT_TRANSCRIPT_FINAL


async def test_vapi_legacy_flat_shapes_still_parse():
    adapter = VapiAdapter()
    events = await adapter.parse_event(
        {"type": "message", "role": "user", "text": CALLER_TEXT, "call_id": "c2"}
    )
    assert events and events[0].type == EventTypes.CALLER_TRANSCRIPT_FINAL
    events = await adapter.parse_event({"type": "function-call", "name": "book_appointment"})
    assert events and events[0].data["tool_name"] == "book_appointment"
    events = await adapter.parse_event({"type": "call-end", "call_id": "c2"})
    assert events and events[0].type == EventTypes.SESSION_ENDED


async def test_vapi_partial_transcript_and_session_id_from_call():
    adapter = VapiAdapter()
    events = await adapter.parse_event(
        {
            "message": {"type": "transcript", "role": "user", "transcriptType": "partial", "transcript": "I was"},
            "call": {"id": "call_abc"},
        }
    )
    assert events and events[0].type == EventTypes.CALLER_TRANSCRIPT_PARTIAL
    assert events[0].session_id == "call_abc"


async def test_bland_end_of_call_webhook_full_payload():
    """The real documented end-of-call payload: transcripts[].user in {user,assistant,robot}."""
    adapter = BlandAdapter()
    events = await adapter.parse_event(
        {
            "call_id": "c3",
            "completed": True,
            "call_length": 1.5,
            "summary": "Caller reported a rear-end collision.",
            "concatenated_transcript": f"user: {CALLER_TEXT} assistant: {AGENT_TEXT}",
            "transcripts": [
                {"id": 1, "user": "assistant", "text": AGENT_TEXT},
                {"id": 2, "user": "user", "text": CALLER_TEXT},
                {"id": 3, "user": "robot", "text": "Call transferred."},
            ],
            "recording_url": "https://recordings.example/c3.wav",
        }
    )
    types = [e.type for e in events]
    assert types.count(EventTypes.CALLER_TRANSCRIPT_FINAL) == 1
    assert types.count(EventTypes.AGENT_TRANSCRIPT_FINAL) == 2  # assistant + robot
    assert EventTypes.TRANSCRIPT_AVAILABLE in types
    assert EventTypes.RECORDING_AVAILABLE in types
    assert types[-1] == EventTypes.SESSION_ENDED


async def test_gpt_realtime_ga_event_names():
    """GA renamed response.audio_transcript.* -> response.output_audio_transcript.*."""
    adapter = GPTRealtimeAdapter()
    events = await adapter.parse_event(
        {"type": "response.output_audio_transcript.delta", "delta": "I'm so", "session_id": "c4"}
    )
    assert events and events[0].type == EventTypes.AGENT_TRANSCRIPT_PARTIAL
    events = await adapter.parse_event(
        {"type": "response.output_audio_transcript.done", "transcript": AGENT_TEXT, "session_id": "c4"}
    )
    assert events and events[0].type == EventTypes.AGENT_TRANSCRIPT_FINAL
    events = await adapter.parse_event(
        {
            "type": "conversation.item.input_audio_transcription.completed",
            "transcript": CALLER_TEXT,
            "session_id": "c4",
        }
    )
    assert events and events[0].type == EventTypes.CALLER_TRANSCRIPT_FINAL
    assert events[0].text == CALLER_TEXT


async def test_grok_cumulative_input_transcription_is_partial():
    """xAI renames OpenAI's .delta to .updated and sends the CUMULATIVE transcript."""
    adapter = GrokAdapter()
    events = await adapter.parse_event(
        {
            "type": "conversation.item.input_audio_transcription.updated",
            "transcript": "I was rear-ended at a red",
            "session_id": "c6",
        }
    )
    assert events and events[0].type == EventTypes.CALLER_TRANSCRIPT_PARTIAL
    events = await adapter.parse_event({"type": "conversation.created", "session_id": "c6"})
    assert events and events[0].type == EventTypes.SESSION_STARTED


async def test_elevenlabs_chat_response_part_and_correction():
    adapter = ElevenLabsAdapter()
    events = await adapter.parse_event(
        {
            "type": "agent_chat_response_part",
            "text_response_part": {"type": "delta", "text": "I'm so sorry"},
            "session_id": "c7",
        }
    )
    assert events and events[0].type == EventTypes.AGENT_TRANSCRIPT_PARTIAL
    events = await adapter.parse_event(
        {
            "type": "agent_response_correction",
            "agent_response_correction_event": {
                "original_agent_response": "Let me finish the whole...",
                "corrected_agent_response": "Let me stop there.",
            },
            "session_id": "c7",
        }
    )
    assert events and events[0].type == EventTypes.AGENT_TRANSCRIPT_FINAL
    assert events[0].text == "Let me stop there."


async def test_deepgram_compile_uses_documented_message_fields():
    """UpdatePrompt carries 'prompt'; InjectAgentMessage carries 'message' (not 'content')."""
    adapter = DeepgramAdapter()
    state = build_initial_state(provider="deepgram", session_id="s1")
    actions = await adapter.compile(RuntimeDecision.inject_hidden_instruction("whisper"), state)
    assert actions[0].payload == {"type": "UpdatePrompt", "prompt": "whisper"}
    actions = await adapter.compile(
        RuntimeDecision.request_field_repair("email", "Please repeat the email."), state
    )
    assert actions[0].payload["type"] == "InjectAgentMessage"
    assert actions[0].payload["message"] == "Please repeat the email."
    assert "content" not in actions[0].payload


async def test_pipecat_llm_text_streams_partial_and_whisper_never_forces_turn():
    adapter = PipecatAdapter()
    events = await adapter.parse_event({"frame": "LLMTextFrame", "text": "I'm", "session_id": "c9"})
    assert events and events[0].type == EventTypes.AGENT_TRANSCRIPT_PARTIAL
    state = build_initial_state(provider="pipecat", session_id="s1")
    actions = await adapter.compile(RuntimeDecision.inject_hidden_instruction("whisper"), state)
    assert actions[0].payload["run_llm"] is False


async def test_ultravox_accepts_rest_role_spelling():
    """Real Ultravox REST artifacts spell roles MESSAGE_ROLE_USER/AGENT (verified live)."""
    adapter = UltravoxAdapter()
    events = await adapter.parse_event(
        {"type": "transcript", "role": "MESSAGE_ROLE_USER", "text": CALLER_TEXT, "final": True}
    )
    assert events and events[0].type == EventTypes.CALLER_TRANSCRIPT_FINAL
    events = await adapter.parse_event(
        {"type": "transcript", "role": "MESSAGE_ROLE_AGENT", "text": AGENT_TEXT, "final": True}
    )
    assert events and events[0].type == EventTypes.AGENT_TRANSCRIPT_FINAL


async def test_generic_adapter_is_configurable():
    adapter = GenericWebhookAdapter(provider_name="acme", inject_action_kind="acme_note", inject_text_key="note")
    decision = RuntimeDecision.inject_hidden_instruction("hello")
    state = build_initial_state(provider="acme", session_id="s1")
    actions = await adapter.compile(decision, state)
    assert actions[0].provider == "acme"
    assert actions[0].kind == "acme_note"
    assert actions[0].payload == {"note": "hello"}


async def test_unknown_payloads_parse_to_nothing():
    for name in ALL:
        events = await CASES[name].adapter.parse_event({"type": "totally_unknown_event_kind"})
        assert events == [] or all(e.type for e in events)
