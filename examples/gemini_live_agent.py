"""Gemini Live + SupafoneLabs: clientContent(turnComplete:false) is the whisper.

Google's Live API uses bidirectional WebSocket sessions. Gemini has no
``system`` role — content roles are ``user`` and ``model`` only. The whisper
therefore uses an incomplete ``user`` turn: ``clientContent`` with
``turnComplete: false``. The model reads the injected text as additional
context without treating it as a completed user turn (so it doesn't
immediately respond to the whisper itself).

The adapter compiles the complete wire message, so this loop sends
``action.payload`` unchanged.

    pip install supafone-labs[all,stt]
    GOOGLE_API_KEY=... python gemini_live_agent.py
"""
import asyncio
import json
import os

import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

import supafone_labs

brain = supafone_labs.SupafoneLabs(provider="gemini_live", scenario="support", mode="return")

MODEL = "gemini-3.1-flash-live-preview"
API_KEY = os.environ["GOOGLE_API_KEY"]
WS_URL = (
    f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage"
    f".v1beta.GenerativeService.BidiGenerateContent?key={API_KEY}"
)


async def main() -> None:
    async with websockets.connect(WS_URL) as ws:
        # Setup message — configure the model and system instruction.
        await ws.send(json.dumps({
            "setup": {
                "model": f"models/{MODEL}",
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Puck"}},
                    },
                },
                "systemInstruction": {
                    "parts": [{"text": "You are a helpful customer support agent."}],
                },
            }
        }))

        # Wait for setupComplete before streaming.
        setup_raw = await ws.recv()
        setup_resp = json.loads(setup_raw)
        if "setupComplete" not in setup_resp:
            print("setup failed:", setup_resp)
            return
        print("Gemini Live session established")

        # Feed the session into the oracle.
        await brain.observe(setup_resp)

        try:
            async for raw in ws:
                if isinstance(raw, (bytes, bytearray)):
                    continue  # skip raw audio chunks
                event = json.loads(raw)
                result = await brain.observe(event)
                for action in result.actions:
                    if action.kind == "client_content":
                        # Incomplete user turn — Gemini reads it as context,
                        # never speaks it back to the caller.
                        await ws.send(json.dumps(action.payload))
                        print("whispered via clientContent(turnComplete:false)")
        except (ConnectionClosedOK, ConnectionClosedError):
            print("session ended")


asyncio.run(main())