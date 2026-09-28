from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any

import pytest


async def wait_json(
    websocket,
    accepted: Callable[[dict[str, Any]], bool],
    *,
    timeout: float = 30,
) -> dict[str, Any]:
    deadline = asyncio.get_running_loop().time() + timeout
    seen: list[str] = []
    while asyncio.get_running_loop().time() < deadline:
        try:
            raw = await asyncio.wait_for(
                websocket.recv(),
                timeout=deadline - asyncio.get_running_loop().time(),
            )
        except TimeoutError:
            break
        if isinstance(raw, (bytes, bytearray)):
            continue
        event = json.loads(raw)
        event_type = str(event.get("type") or next(iter(event), ""))
        seen.append(event_type)
        if event.get("type") in {"error", "response.failed", "response.cancelled"} or event.get(
            "error"
        ):
            pytest.fail(f"provider rejected injection: {event}")
        if accepted(event):
            return event
    pytest.fail(f"provider did not acknowledge injection; events={seen[-12:]}")


async def wait_for_grok_completion(websocket, *, timeout: float = 30) -> dict[str, Any]:
    await wait_json(
        websocket,
        lambda event: event.get("type") == "response.created",
        timeout=timeout,
    )
    completed = await wait_json(
        websocket,
        lambda event: event.get("type") == "response.done",
        timeout=timeout,
    )
    response = completed.get("response")
    status = str(response.get("status") or "") if isinstance(response, dict) else ""
    if status and status != "completed":
        pytest.fail(f"provider did not complete injected response: {completed}")
    return completed
