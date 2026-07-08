"""SignalWire + any voice agent + SupafoneLabs.

SignalWire is Twilio-compatible: the cXML `<Start><Stream>` verb forks call
audio to your websocket with the exact Twilio media-frame shape, so the tap
wiring is byte-for-byte the Twilio example. Only the webhook reply dialect
(cXML) and the domain differ.

    pip install supafone-labs[all,stt] fastapi uvicorn
    DEEPGRAM_API_KEY=... BASE_URL=https://your-host \
      uvicorn telephony_signalwire_tap:app --port 8080
    # Point your SignalWire number's voice handler at POST {BASE_URL}/incoming
"""
import json
import os

from fastapi import FastAPI, WebSocket
from fastapi.responses import Response

import supafone_labs
from supafone_labs.stt import MultilingualCallTap

app = FastAPI()
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")

brain = supafone_labs.SupafoneLabs(
    provider="deepgram",
    inject_via="elevenlabs",        # whoever runs your agent
    scenario="medical_frontdesk",
    mode="return",
)
taps: dict[str, MultilingualCallTap] = {}


@app.post("/incoming")
async def incoming() -> Response:
    """cXML: fork audio to the tap, then hand the call to your agent's SIP/stream."""
    cxml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Start><Stream url="{BASE_URL.replace('http', 'ws')}/media" track="both_tracks"/></Start>
  <!-- Connect the caller to your voice agent here (SIP <Dial>, <Connect><Stream>, etc.) -->
</Response>"""
    return Response(content=cxml, media_type="text/xml")


@app.websocket("/media")
async def media(ws: WebSocket):
    await ws.accept()
    call_sid = "signalwire"
    try:
        while True:
            frame = json.loads(await ws.receive_text())
            event = frame.get("event")
            if event == "start":
                call_sid = frame["start"].get("callSid", call_sid)
                taps[call_sid] = MultilingualCallTap(
                    brain, session_id=call_sid, encoding="mulaw", sample_rate=8000
                )
            elif event == "media" and call_sid in taps:
                await taps[call_sid].feed(
                    track=frame["media"].get("track", "inbound"),
                    payload_b64=frame["media"]["payload"],
                )
            elif event == "stop":
                break
    finally:
        tap = taps.pop(call_sid, None)
        if tap is not None:
            await tap.close()
