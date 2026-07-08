"""ElevenLabs Agents + SupafoneLabs: contextual_update is the native whisper.

Connects to a Conversational AI agent, taps every event, and injects the
directive as a contextual update — text the agent reads but never speaks.
(Verified against the live ElevenLabs API in the repo's test suite.)

    pip install supafone-labs[all,stt]
    ELEVENLABS_API_KEY=... ELEVENLABS_AGENT_ID=... python elevenlabs_agent.py
"""
import asyncio
import json
import os

import websockets

import supafone_labs

brain = supafone_labs.SupafoneLabs(provider="elevenlabs", scenario="support", mode="return")


async def main() -> None:
    url = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={os.environ['ELEVENLABS_AGENT_ID']}"
    async with websockets.connect(
        url, additional_headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}
    ) as ws:
        async for raw in ws:
            if isinstance(raw, (bytes, bytearray)):
                continue
            frame = json.loads(raw)
            if frame.get("type") == "ping":
                await ws.send(json.dumps({"type": "pong", "event_id": frame["ping_event"]["event_id"]}))
                continue
            result = await brain.observe(frame)
            if result.actions and result.actions[0].kind == "contextual_update":
                await ws.send(json.dumps(result.actions[0].payload))
                print("whispered:", result.directive.composed_text())


asyncio.run(main())
