"""Nudge telemetry — every whisper lands in your cloud console, auditable.

When a SUPAFONE_LABS_API_KEY is set, each directive the brain produces is reported
to ``POST /v1/events/nudge`` so the console's log view shows what your second
mind actually told your agents, per call, in real time. Reporting is:

- **fire-and-forget** — scheduled as a background task, never awaited on the
  call path, wrapped so it can never raise into a call;
- **zero-billed** — nudge events cost 0 seconds; they're observability, not usage;
- **off by default without a key**, and disabled entirely with
  ``SupafoneLabs(telemetry=False)`` or ``SUPAFONE_LABS_TELEMETRY=off``.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from supafone_labs.llm.hosted_provider import DEFAULT_API_BASE
from supafone_labs.tiers import license_key

logger = logging.getLogger("supafone_labs.telemetry")


def _enabled() -> bool:
    if os.getenv("SUPAFONE_LABS_TELEMETRY", "").lower() in {"off", "0", "false"}:
        return False
    return bool(license_key())


async def report_nudge(
    *,
    session_id: str,
    provider: str,
    text: str,
    confidence: float = 0.0,
    injected: bool = False,
    kind: str = "",
    language: str = "",
    emotion: str = "",
    intent: str = "",
    urgency: float = 0.0,
    latency_ms: float = 0.0,
    model: str = "",
    turns: int = 0,
    client: Any = None,
) -> bool:
    """POST one fully-granular nudge to the cloud log. Returns success; never raises."""
    if not text or not _enabled():
        return False
    base = (os.getenv("SUPAFONE_LABS_API_BASE") or DEFAULT_API_BASE).rstrip("/")
    owns_client = client is None
    try:
        if owns_client:
            import httpx

            client = httpx.AsyncClient(timeout=5)
        resp = await client.post(
            f"{base}/events/nudge",
            headers={"Authorization": f"Bearer {license_key()}"},
            json={
                "session_id": session_id,
                "provider": provider,
                "text": text,
                "confidence": confidence,
                "injected": injected,
                "kind": kind,
                "language": language,
                "emotion": emotion,
                "intent": intent,
                "urgency": urgency,
                "latency_ms": latency_ms,
                "model": model,
                "turns": turns,
            },
        )
        return resp.status_code in (200, 201)
    except Exception:
        logger.debug("nudge telemetry failed (call unaffected)", exc_info=True)
        return False
    finally:
        if owns_client and client is not None:
            try:
                await client.aclose()
            except Exception:
                pass


def report_nudge_soon(**kwargs: Any) -> None:
    """Schedule report_nudge as a background task if a loop is running."""
    if not _enabled():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(report_nudge(**kwargs))


async def report_call(
    *,
    session_id: str,
    agent: str = "default",
    score: float = 0.0,
    outcome: str = "",
    summary: str = "",
    nudges: int = 0,
    turns: int = 0,
    language: str = "",
    client: Any = None,
) -> bool:
    """POST one post-call report to the cloud (zero-billed). Never raises."""
    if not _enabled():
        return False
    base = (os.getenv("SUPAFONE_LABS_API_BASE") or DEFAULT_API_BASE).rstrip("/")
    owns_client = client is None
    try:
        if owns_client:
            import httpx

            client = httpx.AsyncClient(timeout=5)
        resp = await client.post(
            f"{base}/events/call_report",
            headers={"Authorization": f"Bearer {license_key()}"},
            json={
                "session_id": session_id, "agent": agent, "score": score,
                "outcome": outcome, "summary": summary, "nudges": nudges,
                "turns": turns, "language": language,
            },
        )
        return resp.status_code in (200, 201)
    except Exception:
        logger.debug("call-report telemetry failed (call unaffected)", exc_info=True)
        return False
    finally:
        if owns_client and client is not None:
            try:
                await client.aclose()
            except Exception:
                pass


def report_call_soon(**kwargs: Any) -> None:
    if not _enabled():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(report_call(**kwargs))


async def fetch_standing(agent: str = "default", client: Any = None) -> str:
    """Fetch the current self-optimized standing directive for this agent ('' on any failure)."""
    if not _enabled():
        return ""
    base = (os.getenv("SUPAFONE_LABS_API_BASE") or DEFAULT_API_BASE).rstrip("/")
    owns_client = client is None
    try:
        if owns_client:
            import httpx

            client = httpx.AsyncClient(timeout=3)
        resp = await client.get(
            f"{base}/optimizer/standing",
            params={"agent": agent},
            headers={"Authorization": f"Bearer {license_key()}"},
        )
        if resp.status_code != 200:
            return ""
        return str(resp.json().get("text") or "")
    except Exception:
        return ""
    finally:
        if owns_client and client is not None:
            try:
                await client.aclose()
            except Exception:
                pass
