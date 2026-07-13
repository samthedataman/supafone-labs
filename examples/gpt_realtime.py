"""OpenAI Realtime + SupafoneLabs with native live controls.

OpenAI receives a system-role ``conversation.item.create``. The adapter
compiles the complete wire message, so this loop sends ``action.payload``
unchanged. Grok uses a different ``response.create.instructions`` action; use
the same observe/send loop with ``provider="grok"`` and xAI's Realtime socket.

    pip install supafone-labs[all,stt]
    OPENAI_API_KEY=... python gpt_realtime.py
"""
import asyncio
import json
import os

import websockets

import supafone_labs

brain = supafone_labs.SupafoneLabs(provider="gpt_realtime", scenario="sales_outbound", mode="return")
BASE_INSTRUCTIONS = "You are a friendly outbound sales agent for Acme."


async def main() -> None:
    async with websockets.connect(
        "wss://api.openai.com/v1/realtime?model=gpt-realtime",
        additional_headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
    ) as ws:
        await ws.send(json.dumps({
            "type": "session.update",
            "session": {"type": "realtime", "instructions": BASE_INSTRUCTIONS,
                        "audio": {"input": {"transcription": {"model": "whisper-1"}}}},
        }))
        async for raw in ws:
            event = json.loads(raw)
            result = await brain.observe(event)   # GA + beta event names both parse
            for action in result.actions:
                if action.kind == "conversation_item_create":
                    await ws.send(json.dumps(action.payload))
                    print("system context added")


asyncio.run(main())
