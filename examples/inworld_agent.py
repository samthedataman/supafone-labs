"""Inworld Realtime + SupafoneLabs: OpenAI-Realtime-compatible item inject.

Inworld's current Realtime API follows the OpenAI Realtime event protocol —
the whisper is a system-role ``conversation.item.create``, identical to the
OpenAI path. Older character-engine ``text`` packets are also parsed by the
adapter for backward compatibility.

The adapter compiles the complete wire message, so this loop sends
``action.payload`` unchanged.

    pip install supafone-labs[all,stt]
    INWORLD_API_KEY=... INWORLD_WORKSPACE=... python inworld_agent.py
"""
import asyncio
import json
import os

import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

import supafone_labs

brain = supafone_labs.SupafoneLabs(provider="inworld", scenario="support", mode="return")

API_KEY = os.environ["INWORLD_API_KEY"]
WORKSPACE = os.environ.get("INWORLD_WORKSPACE", "default")
WS_URL = os.environ.get(
    "INWORLD_WS_URL",
    f"wss://studio.inworld.ai/v1/session?workspace={WORKSPACE}",
)


async def main() -> None:
    async with websockets.connect(
        WS_URL,
        additional_headers={"Authorization": f"Bearer {API_KEY}"},
    ) as ws:
        # Inworld session.created or conversation.created triggers
        # SESSION_STARTED in the adapter.
        try:
            async for raw in ws:
                if isinstance(raw, (bytes, bytearray)):
                    continue  # skip audio frames
                event = json.loads(raw)
                result = await brain.observe(event)
                for action in result.actions:
                    if action.kind == "conversation_item_create":
                        # System-role item inject — the character reads it as
                        # hidden context, never speaks it to the player/caller.
                        await ws.send(json.dumps(action.payload))
                        print("whispered via conversation.item.create (system)")
        except (ConnectionClosedOK, ConnectionClosedError):
            print("session ended")


asyncio.run(main())