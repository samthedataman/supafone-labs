"""Live model discovery — the registry that never deprecates.

The static ``ORACLE_MODELS`` table in config is a bootstrap/offline fallback
only. The real source of truth is each vendor's live models endpoint:

- Anthropic  ``GET https://api.anthropic.com/v1/models``
- OpenAI     ``GET https://api.openai.com/v1/models``
- xAI        ``GET https://api.x.ai/v1/models``
- Hosted     ``GET {SUPAFONE_LABS_API_BASE}/models`` (the Supafone Labs gateway)

``discover_oracle_models()`` queries whichever vendors you hold keys for,
merges with the static fallback, and caches for an hour. Nothing validates
against the static list at call time — pick any model your key can reach,
including ones released after this package shipped.
"""
from __future__ import annotations

import os
import time
from typing import Any

from supafone_labs.config import ORACLE_MODELS
from supafone_labs.llm.hosted_provider import DEFAULT_API_BASE
from supafone_labs.tiers import license_key

_CACHE: dict[str, Any] = {"at": 0.0, "models": None}
CACHE_TTL_SECONDS = 3600.0


async def _get_json(client: Any, url: str, headers: dict[str, str]) -> Any:
    resp = await client.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


async def _anthropic_models(client: Any) -> list[str]:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        return []
    data = await _get_json(
        client,
        "https://api.anthropic.com/v1/models?limit=100",
        {"x-api-key": key, "anthropic-version": "2023-06-01"},
    )
    return [str(m.get("id")) for m in data.get("data", []) if m.get("id")]


async def _openai_models(client: Any) -> list[str]:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        return []
    data = await _get_json(client, "https://api.openai.com/v1/models", {"Authorization": f"Bearer {key}"})
    ids = [str(m.get("id")) for m in data.get("data", []) if m.get("id")]
    # chat-capable families only — embeddings/audio/image models aren't oracles
    return [i for i in ids if i.startswith(("gpt-", "o1", "o3", "o4"))]


async def _xai_models(client: Any) -> list[str]:
    key = os.getenv("XAI_API_KEY", "")
    if not key:
        return []
    data = await _get_json(client, "https://api.x.ai/v1/models", {"Authorization": f"Bearer {key}"})
    return [str(m.get("id")) for m in data.get("data", []) if m.get("id")]


async def _hosted_models(client: Any) -> list[str]:
    if not license_key():
        return []
    base = (os.getenv("SUPAFONE_LABS_API_BASE") or DEFAULT_API_BASE).rstrip("/")
    data = await _get_json(client, f"{base}/models", {})
    return [str(m.get("id")) for m in data.get("models", []) if m.get("id") and m.get("live", True)]


async def discover_oracle_models(
    *, refresh: bool = False, client: Any = None
) -> dict[str, list[str]]:
    """Return {provider: [model ids]} from live vendor APIs, static fallback merged in.

    Only vendors whose keys are present are queried; failures degrade to the
    static table for that vendor. Results are cached for an hour per process.
    """
    now = time.monotonic()
    if not refresh and _CACHE["models"] is not None and now - _CACHE["at"] < CACHE_TTL_SECONDS:
        return _CACHE["models"]

    owns_client = client is None
    if owns_client:
        try:
            import httpx
        except ImportError:
            return {k: list(v) for k, v in ORACLE_MODELS.items()}
        client = httpx.AsyncClient(timeout=10)

    fetchers = {
        "anthropic": _anthropic_models,
        "openai": _openai_models,
        "xai": _xai_models,
        "hosted": _hosted_models,
    }
    merged: dict[str, list[str]] = {}
    try:
        for provider, fetch in fetchers.items():
            live: list[str] = []
            try:
                live = await fetch(client)
            except Exception:
                live = []
            fallback = ORACLE_MODELS.get(provider, [])
            merged[provider] = live or list(fallback)
    finally:
        if owns_client:
            await client.aclose()

    _CACHE["models"] = merged
    _CACHE["at"] = now
    return merged


def clear_model_cache() -> None:
    _CACHE["models"] = None
    _CACHE["at"] = 0.0
