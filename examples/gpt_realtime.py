"""OpenAI Realtime (or xAI Grok) + SupafoneLabs: session.update is the whisper.

Speech-to-speech models have no out-of-band message channel — the prompt patch
IS the silent coaching path. Works identically for Grok's Voice Agent API
(swap the URL for wss://api.x.ai/v1/realtime?model=grok-voice-latest and
provider="grok").

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
        whispered: list[str] = []
        async for raw in ws:
            event = json.loads(raw)
            result = await brain.observe(event)   # GA + beta event names both parse
            if result.actions and result.actions[0].kind == "session_update":
                whispered.append(result.actions[0].payload["instructions_append"])
                await ws.send(json.dumps({
                    "type": "session.update",
                    "session": {"type": "realtime",
                                "instructions": BASE_INSTRUCTIONS + "\n\n" + "\n".join(whispered[-3:])},
                }))
                print("instructions patched:", whispered[-1])


asyncio.run(main())
