"""Grok (xAI) Realtime + SupafoneLabs: response.create.instructions is the whisper.

xAI's Voice Agent API is OpenAI-Realtime-*compatible* but not identical:
transcription arrives as ``conversation.item.input_audio_transcription.updated``
carrying the **cumulative** transcript, and the whisper primitive is
``response.create`` with an ``instructions`` override (per-response, not
per-session like OpenAI's ``session.update``).

The adapter compiles the complete wire message, so this loop sends
``action.payload`` unchanged.

    pip install supafone-labs[all,stt]
    XAI_API_KEY=... python grok_realtime.py
"""
import asyncio
import json
import os

import websockets

import supafone_labs

brain = supafone_labs.SupafoneLabs(provider="grok", scenario="sales_outbound", mode="return")
BASE_INSTRUCTIONS = "You are a friendly outbound sales agent for Acme."


async def main() -> None:
    async with websockets.connect(
        "wss://api.x.ai/v1/realtime?model=grok-voice-latest",
        additional_headers={"Authorization": f"Bearer {os.environ['XAI_API_KEY']}"},
    ) as ws:
        # Configure the session: enable transcription so the oracle can read
        # what the caller says (xAI uses grok-transcribe, not whisper-1).
        await ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "type": "realtime",
                "instructions": BASE_INSTRUCTIONS,
                "audio": {"input": {"transcription": {"model": "grok-transcribe"}}},
            },
        }))
        async for raw in ws:
            event = json.loads(raw)
            result = await brain.observe(event)
            for action in result.actions:
                if action.kind == "response_create":
                    # xAI's per-response instruction override — the agent reads
                    # it silently before generating its next spoken reply.
                    await ws.send(json.dumps(action.payload))
                    print("whispered via response.create.instructions")


asyncio.run(main())
