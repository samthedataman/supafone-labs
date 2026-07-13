"""Credentialed acceptance probes for native mid-call injection channels.

Every test sends the action compiled by the production adapter and waits for
the provider's documented acknowledgement (or a completed next turn when the
provider defines no direct acknowledgement). Missing credentials are skips,
never passes.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Callable

import pytest

from supafone_labs.runtime.adapters import (
    DeepgramAdapter,
    GeminiLiveAdapter,
    GPTRealtimeAdapter,
    GrokAdapter,
    InworldAdapter,
    UltravoxAdapter,
    VapiAdapter,
)
from supafone_labs.runtime.core.decision import RuntimeDecision
from supafone_labs.runtime.core.state import build_initial_state

pytestmark = [pytest.mark.live, pytest.mark.live_injection]


def needs(*variables: str):
    missing = [name for name in variables if not os.getenv(name)]
    return pytest.mark.skipif(bool(missing), reason=f"missing live credentials: {', '.join(missing)}")


async def _action(adapter):
    state = build_initial_state(provider=adapter.provider_name, session_id="live-injection")
    actions = await adapter.compile(
        RuntimeDecision.inject_hidden_instruction(
            "Live contract probe: keep the next response concise and friendly."
        ),
        state,
    )
    assert len(actions) == 1
    return actions[0]


async def _wait_json(
    websocket,
    accepted: Callable[[dict[str, Any]], bool],
    *,
    timeout: float = 30,
) -> dict[str, Any]:
    deadline = asyncio.get_running_loop().time() + timeout
    seen: list[str] = []
    while asyncio.get_running_loop().time() < deadline:
        raw = await asyncio.wait_for(websocket.recv(), timeout=deadline - asyncio.get_running_loop().time())
        if isinstance(raw, (bytes, bytearray)):
            continue
        event = json.loads(raw)
        event_type = str(event.get("type") or next(iter(event), ""))
        seen.append(event_type)
        if event.get("type") == "error" or event.get("error"):
            pytest.fail(f"provider rejected injection: {event}")
        if accepted(event):
            return event
    pytest.fail(f"provider did not acknowledge injection; events={seen[-12:]}")


@needs("ULTRAVOX_API_KEY", "ULTRAVOX_LIVE_CALL_ID")
async def test_live_ultravox_deferred_instruction_returns_204():
    httpx = pytest.importorskip("httpx")
    action = await _action(UltravoxAdapter())
    url = (
        "https://api.ultravox.ai/api/calls/"
        f"{os.environ['ULTRAVOX_LIVE_CALL_ID']}/send_data_message"
    )
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            headers={"X-API-Key": os.environ["ULTRAVOX_API_KEY"]},
            json=action.payload,
        )
    assert response.status_code == 204, response.text


@needs("OPENAI_API_KEY")
async def test_live_openai_realtime_accepts_system_conversation_item():
    websockets = pytest.importorskip("websockets")
    model = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime")
    action = await _action(GPTRealtimeAdapter())
    async with websockets.connect(
        f"wss://api.openai.com/v1/realtime?model={model}",
        additional_headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
    ) as ws:
        await _wait_json(ws, lambda event: event.get("type") == "session.created")
        await ws.send(json.dumps(action.payload))
        event = await _wait_json(
            ws,
            lambda item: item.get("type") in {
                "conversation.item.created",
                "conversation.item.done",
            }
            and (item.get("item") or {}).get("role") == "system",
        )
    assert (event.get("item") or {}).get("role") == "system"


@needs("VAPI_CONTROL_URL")
async def test_live_vapi_control_url_accepts_system_message():
    httpx = pytest.importorskip("httpx")
    action = await _action(VapiAdapter())
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            os.environ["VAPI_CONTROL_URL"],
            headers={"Content-Type": "application/json"},
            json=action.payload,
        )
    assert 200 <= response.status_code < 300, response.text


@needs("XAI_API_KEY")
async def test_live_grok_accepts_per_response_instructions():
    websockets = pytest.importorskip("websockets")
    model = os.getenv("XAI_VOICE_MODEL", "grok-voice-latest")
    action = await _action(GrokAdapter())
    async with websockets.connect(
        f"wss://api.x.ai/v1/realtime?model={model}",
        additional_headers={"Authorization": f"Bearer {os.environ['XAI_API_KEY']}"},
    ) as ws:
        await _wait_json(
            ws,
            lambda event: event.get("type") in {"conversation.created", "session.created"},
        )
        await ws.send(json.dumps(action.payload))
        accepted = await _wait_json(ws, lambda event: event.get("type") == "response.created")
    assert accepted["type"] == "response.created"


@needs("INWORLD_API_KEY")
async def test_live_inworld_accepts_system_conversation_item():
    websockets = pytest.importorskip("websockets")
    action = await _action(InworldAdapter())
    url = os.getenv(
        "INWORLD_REALTIME_WS_URL",
        f"wss://api.inworld.ai/api/v1/realtime/session?key=sf-{time.time_ns()}&protocol=realtime",
    )
    scheme = os.getenv("INWORLD_AUTH_SCHEME", "Basic")
    async with websockets.connect(
        url,
        additional_headers={"Authorization": f"{scheme} {os.environ['INWORLD_API_KEY']}"},
    ) as ws:
        await _wait_json(ws, lambda event: event.get("type") == "session.created")
        await ws.send(json.dumps(action.payload))
        accepted = await _wait_json(
            ws,
            lambda event: event.get("type") in {
                "conversation.item.added",
                "conversation.item.created",
                "conversation.item.done",
            }
            and (event.get("item") or {}).get("role") == "system",
        )
    assert (accepted.get("item") or {}).get("role") == "system"


@needs("DEEPGRAM_API_KEY")
async def test_live_deepgram_update_prompt_receives_prompt_updated():
    websockets = pytest.importorskip("websockets")
    action = await _action(DeepgramAdapter())
    settings = {
        "type": "Settings",
        "audio": {
            "input": {"encoding": "linear16", "sample_rate": 16000},
            "output": {"encoding": "linear16", "sample_rate": 24000, "container": "none"},
        },
        "agent": {
            "listen": {"provider": {"type": "deepgram", "model": "nova-3"}},
            "think": {
                "provider": {"type": "open_ai", "model": "gpt-4o-mini"},
                "prompt": "You are a concise test agent.",
            },
            "speak": {"provider": {"type": "deepgram", "model": "aura-2-thalia-en"}},
        },
    }
    if os.getenv("DEEPGRAM_LIVE_SETTINGS_JSON"):
        settings = json.loads(os.environ["DEEPGRAM_LIVE_SETTINGS_JSON"])
    async with websockets.connect(
        "wss://agent.deepgram.com/v1/agent/converse",
        additional_headers={"Authorization": f"Token {os.environ['DEEPGRAM_API_KEY']}"},
    ) as ws:
        await _wait_json(ws, lambda event: event.get("type") == "Welcome")
        await ws.send(json.dumps(settings))
        await _wait_json(ws, lambda event: event.get("type") == "SettingsApplied")
        await ws.send(json.dumps(action.payload))
        accepted = await _wait_json(ws, lambda event: event.get("type") == "PromptUpdated")
    assert accepted["type"] == "PromptUpdated"


@needs("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION", "GEMINI_LIVE_MODEL")
async def test_live_gemini_system_turn_changes_next_response():
    google = pytest.importorskip("google.genai")
    types = pytest.importorskip("google.genai.types")
    action = await _action(GeminiLiveAdapter())
    turn = action.payload["clientContent"]["turns"][0]
    client = google.Client(
        vertexai=True,
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        location=os.environ["GOOGLE_CLOUD_LOCATION"],
    )
    model = os.environ["GEMINI_LIVE_MODEL"]
    async with client.aio.live.connect(
        model=model,
        config={"response_modalities": ["AUDIO"], "output_audio_transcription": {}},
    ) as session:
        await session.send_client_content(
            turns=types.Content(
                role=turn["role"],
                parts=[types.Part(text=turn["parts"][0]["text"])],
            ),
            turn_complete=False,
        )
        await session.send_client_content(
            turns=types.Content(
                role="user",
                parts=[types.Part(text="Say hello in five words or fewer.")],
            ),
            turn_complete=True,
        )
        saw_output = False
        async for message in session.receive():
            if message.text or (
                message.server_content and message.server_content.output_transcription
            ):
                saw_output = True
            if message.server_content and message.server_content.turn_complete:
                break
    assert saw_output
