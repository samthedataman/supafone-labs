"""Telnyx + any voice agent + SupafoneLabs.

Telnyx Call Control streams call media over a websocket you choose
(`stream_url` on the answer/dial command, `stream_track="both_tracks"`).
Frames are Twilio-shaped: {"event": "media", "media": {"track", "payload"}} —
so the tap wiring is identical; only the answer flow differs.

    pip install supafone-labs[all,stt] fastapi uvicorn httpx
    TELNYX_API_KEY=... DEEPGRAM_API_KEY=... BASE_URL=https://your-host \
      uvicorn telephony_telnyx_tap:app --port 8080
    # Point your Telnyx Call Control app's webhook at POST {BASE_URL}/telnyx/events
"""
import json
import os

import httpx
from fastapi import FastAPI, Request, WebSocket

import supafone_labs
from supafone_labs.stt import MultilingualCallTap

app = FastAPI()
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")

brain = supafone_labs.SupafoneLabs(
    provider="deepgram",
    inject_via="ultravox",          # whoever runs your agent: vapi / retell / elevenlabs / ...
    scenario="support",
    mode="return",
)
taps: dict[str, MultilingualCallTap] = {}


@app.post("/telnyx/events")
async def telnyx_events(request: Request):
    """Call Control webhook: answer inbound calls with media streaming enabled."""
    event = (await request.json()).get("data", {})
    if event.get("event_type") == "call.initiated":
        call_id = event["payload"]["call_control_id"]
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"https://api.telnyx.com/v2/calls/{call_id}/actions/answer",
                headers={"Authorization": f"Bearer {os.environ['TELNYX_API_KEY']}"},
                json={
                    "stream_url": f"{BASE_URL.replace('http', 'ws')}/telnyx/media?call_id={call_id}",
                    "stream_track": "both_tracks",
                },
            )
    return {"ok": True}


@app.websocket("/telnyx/media")
async def telnyx_media(ws: WebSocket):
    await ws.accept()
    call_id = ws.query_params.get("call_id", "unknown")
    tap = taps[call_id] = MultilingualCallTap(
        brain, session_id=call_id, encoding="mulaw", sample_rate=8000
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
        await taps.pop(call_id, tap).close()
