"""Deepgram Voice Agent + SupafoneLabs: UpdatePrompt is the silent channel.

Attach to a Voice Agent session, tap ConversationText, and patch the live
prompt with the oracle's directive (Deepgram ADDS to the prompt, per docs).

    pip install supafone-labs[all,stt]
    DEEPGRAM_API_KEY=... python deepgram_voice_agent.py
"""
import asyncio
import json
import os

import websockets

import supafone_labs

brain = supafone_labs.SupafoneLabs(provider="deepgram", scenario="medical_frontdesk", mode="return")

SETTINGS = {
    "type": "Settings",
    "audio": {"input": {"encoding": "linear16", "sample_rate": 16000},
              "output": {"encoding": "linear16", "sample_rate": 24000}},
    "agent": {
        "listen": {"provider": {"type": "deepgram", "model": "nova-3"}},
        "think": {"provider": {"type": "anthropic", "model": "claude-haiku-4-5-20251001"},
                  "prompt": "You are a friendly front-desk agent."},
        "speak": {"provider": {"type": "deepgram", "model": "aura-2-thalia-en"}},
    },
}


async def main() -> None:
    async with websockets.connect(
        "wss://agent.deepgram.com/v1/agent/converse",
        additional_headers={"Authorization": f"Token {os.environ['DEEPGRAM_API_KEY']}"},
    ) as ws:
        await ws.send(json.dumps(SETTINGS))
        async for raw in ws:
            if isinstance(raw, (bytes, bytearray)):
                continue  # agent audio out — pipe to your telephony leg
            msg = json.loads(raw)
            result = await brain.observe(msg)
            if result.actions and result.actions[0].kind == "update_prompt":
                await ws.send(json.dumps(result.actions[0].payload))
                print("prompt patched:", result.directive.composed_text())


asyncio.run(main())
