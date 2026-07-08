"""Vapi + SupafoneLabs: a server-URL webhook that whispers back.

Point your Vapi assistant's Server URL here. Vapi POSTs `{"message": {...}}`
envelopes; confident directives return as an assistant override the next turn.

    pip install supafone-labs[all] fastapi uvicorn
    uvicorn vapi_webhook_server:app --port 8080
"""
from fastapi import FastAPI

import supafone_labs

app = FastAPI()
brain = supafone_labs.SupafoneLabs(provider="vapi", scenario="support", mode="return")


@app.post("/vapi/webhook")
async def vapi_webhook(payload: dict):
    result = await brain.observe(payload)
    if result.actions and result.actions[0].kind == "assistant_override":
        # Vapi lets a server response steer the assistant for the next turn.
        return {
            "assistant": {
                "model": {
                    "messages": [
                        {"role": "system", "content": result.actions[0].payload["instruction"]}
                    ]
                }
            }
        }
    return {}
