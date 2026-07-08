"""Any SIP trunk + SupafoneLabs: fork the audio, get a multilingual second mind.

Twilio shown here (<Stream track="both_tracks"> to this websocket) — Telnyx,
SignalWire, Vonage, Plivo, Jambonz, and FreeSWITCH/Asterisk media forks are the
same pattern: raw audio in, language-tagged canonical transcripts into the
brain via Deepgram nova-3 `language=multi` (or the hosted proxy with a
SUPAFONE_LABS_API_KEY and zero Deepgram account).

    pip install supafone-labs[all,stt] fastapi uvicorn
    uvicorn twilio_sip_multilingual_tap:app --port 8080
    # TwiML: <Start><Stream url="wss://your-host/media" track="both_tracks"/></Start>
"""
import json

from fastapi import FastAPI, WebSocket

import supafone_labs
from supafone_labs.stt import MultilingualCallTap

app = FastAPI()
brain = supafone_labs.SupafoneLabs(provider="deepgram", scenario="legal_intake", mode="return")
taps: dict[str, MultilingualCallTap] = {}


@app.websocket("/media")
async def twilio_media(ws: WebSocket):
    await ws.accept()
    call_sid = ""
    try:
        while True:
            frame = json.loads(await ws.receive_text())
            event = frame.get("event")
            if event == "start":
                call_sid = frame["start"]["callSid"]
                taps[call_sid] = MultilingualCallTap(
                    brain, session_id=call_sid, encoding="mulaw", sample_rate=8000
                )
            elif event == "media" and call_sid in taps:
                await taps[call_sid].feed(
                    track=frame["media"].get("track", "inbound"),
                    payload_b64=frame["media"]["payload"],
                )
                # The brain's state/directives update live; deliver them
                # wherever your agent runs (see the other examples).
            elif event == "stop" and call_sid in taps:
                await taps.pop(call_sid).close()
    except Exception:
        if call_sid in taps:
            await taps.pop(call_sid).close()
