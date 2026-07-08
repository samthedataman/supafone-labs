"""Retell + SupafoneLabs: the custom-LLM websocket with a second mind in the loop.

Retell connects to YOUR websocket at /llm-websocket/{call_id} and streams
`interaction_type` messages. The directive lands as a system message prepended
to your model call — Retell's native "hidden instruction" path.

    pip install supafone-labs[all] fastapi uvicorn openai
    uvicorn retell_custom_llm:app --port 8080
"""
import json

from fastapi import FastAPI, WebSocket

import supafone_labs

app = FastAPI()
brain = supafone_labs.SupafoneLabs(provider="retell", scenario="legal_intake", mode="return")


async def run_your_llm(transcript: list[dict], extra_system: str | None) -> str:
    """Your normal response generation — swap in your model of choice."""
    messages = [{"role": "system", "content": "You are a helpful intake agent."}]
    if extra_system:
        messages.append({"role": "system", "content": extra_system})  # the whisper
    messages += [
        {"role": "assistant" if t["role"] == "agent" else "user", "content": t["content"]}
        for t in transcript
    ]
    # ... call OpenAI/Anthropic here ...
    return "Thanks — tell me what happened."


@app.websocket("/llm-websocket/{call_id}")
async def retell_llm(ws: WebSocket, call_id: str):
    await ws.accept()
    await ws.send_text(json.dumps({"response_type": "config", "config": {"auto_reconnect": True}}))
    while True:
        msg = json.loads(await ws.receive_text())
        msg.setdefault("call_id", call_id)
        result = await brain.observe(msg)  # tap every interaction_type
        if msg.get("interaction_type") in {"response_required", "reminder_required"}:
            whisper = None
            if result.actions and result.actions[0].kind == "llm_context_inject":
                whisper = result.actions[0].payload["content"]
            content = await run_your_llm(msg.get("transcript", []), whisper)
            await ws.send_text(json.dumps({
                "response_type": "response",
                "response_id": msg["response_id"],
                "content": content,
                "content_complete": True,
            }))
