"""Vapi + SupafoneLabs: live call control from a server-URL webhook.

Point your Vapi assistant's Server URL here. Vapi POSTs `{"message": {...}}`
envelopes. Enable ``monitorPlan.controlEnabled`` so each call includes
``message.call.monitor.controlUrl``; directives are posted there as Vapi's
documented ``add-message`` control.

    pip install supafone-labs[all] fastapi uvicorn httpx
    uvicorn vapi_webhook_server:app --port 8080
"""
import httpx
from fastapi import FastAPI

import supafone_labs

app = FastAPI()
brain = supafone_labs.SupafoneLabs(provider="vapi", scenario="support", mode="return")


@app.post("/vapi/webhook")
async def vapi_webhook(payload: dict):
    result = await brain.observe(payload)
    message = payload.get("message") if isinstance(payload.get("message"), dict) else payload
    call = message.get("call") if isinstance(message.get("call"), dict) else {}
    monitor = call.get("monitor") if isinstance(call.get("monitor"), dict) else {}
    control_url = monitor.get("controlUrl")
    for action in result.actions:
        if action.kind != "control_add_message":
            continue
        if not control_url:
            return {"ok": False, "error": "Vapi monitorPlan.controlEnabled is required"}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(control_url, json=action.payload)
            response.raise_for_status()
    return {"ok": True}
