"""THE relatable one: a Twilio number + an AI voice provider + SupafoneLabs, one file.

This is how real deployments look — the voice provider (Ultravox here) runs the
conversation, Twilio carries the phone call, and SupafoneLabs supervises:

    caller ──> Twilio number
                 ├── <Connect><Stream>  ──> Ultravox   (the agent that talks)
                 └── <Start><Stream>    ──> /media     (a silent audio fork)
                                              │
                                    MultilingualCallTap (Deepgram nova-3 multi)
                                              │
                                        Supafone Labs brain
                                              │  taps as "deepgram",
                                              │  whispers as "ultravox"
                                              ▼
                              inject_message ──> the live Ultravox call

The key line is `inject_via="ultravox"`: SupafoneLabs TAPS the forked audio (so
it hears both sides, in 10 languages) but compiles its whispers for the
platform actually running the call. Swap "ultravox" for your provider and the
same file supervises a Vapi/Retell/ElevenLabs deployment.

    pip install supafone-labs[all,stt] fastapi uvicorn websockets httpx
    ULTRAVOX_API_KEY=... DEEPGRAM_API_KEY=... BASE_URL=https://your-host \
      uvicorn full_stack_twilio_ultravox:app --port 8080
    # then point your Twilio number's voice webhook at POST {BASE_URL}/incoming
"""
import json
import os

import httpx
import websockets
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import Response

import supafone_labs
from supafone_labs.stt import MultilingualCallTap

app = FastAPI()
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")

# One brain per process; per-call state is keyed by session_id internally.
# Taps Deepgram-shaped transcripts, whispers Ultravox-shaped injections.
brain = supafone_labs.SupafoneLabs(
    provider="deepgram",
    inject_via="ultravox",
    scenario="legal_intake",
    oracle_instructions="Never quote fees. Acknowledge injury before logistics.",
    mode="return",
)

taps: dict[str, MultilingualCallTap] = {}
ultravox_sockets: dict[str, object] = {}   # call_sid -> live Ultravox WS


@app.post("/incoming")
async def incoming_call(request: Request) -> Response:
    """Twilio voice webhook: start the Ultravox agent AND the SupafoneLabs fork."""
    form = dict(await request.form())
    call_sid = form.get("CallSid", "unknown")

    # 1) Create the Ultravox call (the agent that will actually talk).
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://api.ultravox.ai/api/calls",
            headers={"X-API-Key": os.environ["ULTRAVOX_API_KEY"]},
            json={
                "systemPrompt": "You are a warm intake agent for Stanley Law.",
                "medium": {"twilio": {}},
            },
        )
        resp.raise_for_status()
        join_url = resp.json()["joinUrl"]

    # 2) Keep a socket to the Ultravox call for whisper delivery.
    ultravox_sockets[call_sid] = await websockets.connect(join_url)

    # 3) TwiML: fork the audio to us, connect the caller to Ultravox.
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Start><Stream url="{BASE_URL.replace('http', 'ws')}/media?call_sid={call_sid}" track="both_tracks"/></Start>
  <Connect><Stream url="{join_url}"/></Connect>
</Response>"""
    return Response(content=twiml, media_type="text/xml")


@app.websocket("/media")
async def media_fork(ws: WebSocket):
    """The silent fork: Twilio media frames -> multilingual tap -> the brain."""
    await ws.accept()
    call_sid = ws.query_params.get("call_sid", "unknown")
    tap = taps[call_sid] = MultilingualCallTap(
        _WhisperingBrain(call_sid), session_id=call_sid, encoding="mulaw", sample_rate=8000
    )
    try:
        while True:
            frame = json.loads(await ws.receive_text())
            if frame.get("event") == "media":
                await tap.feed(
                    track=frame["media"].get("track", "inbound"),
                    payload_b64=frame["media"]["payload"],
                )
            elif frame.get("event") == "stop":
                break
    finally:
        await taps.pop(call_sid, tap).close()
        sock = ultravox_sockets.pop(call_sid, None)
        if sock is not None:
            await sock.close()


class _WhisperingBrain:
    """observe() passthrough that delivers compiled whispers to the live Ultravox WS."""

    def __init__(self, call_sid: str) -> None:
        self.call_sid = call_sid

    async def observe(self, raw: dict, provider: str = "deepgram"):
        result = await brain.observe(raw, provider=provider)
        sock = ultravox_sockets.get(self.call_sid)
        if sock is not None and result.actions and result.actions[0].kind == "inject_message":
            # Send the adapter's audited user_text_message unchanged.
            await sock.send(json.dumps(result.actions[0].payload))
            print(f"[{self.call_sid}] whispered:", result.directive.composed_text())
        return result
