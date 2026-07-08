"""HostedLLMProvider — the paid tier's oracle backend (Supafone Labs' own keys).

POSTs the chat messages to the Supafone Labs cloud (``SUPAFONE_LABS_API_BASE``,
default ``https://api.labs.supafone.ai/v1``) authenticated with the user's
``SUPAFONE_LABS_API_KEY`` license. The server completes the request on
Supafone Labs-managed model keys, so pro users never configure Anthropic/OpenAI
credentials. httpx is imported lazily; an injected client makes it testable.
"""
from __future__ import annotations

import os
from typing import Any

from supafone_labs.tiers import TierError, license_key

DEFAULT_API_BASE = "https://api.labs.supafone.ai/v1"


class HostedLLMProvider:
    """LLMProvider that proxies completion to the Supafone Labs cloud (pro tier)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        client: Any = None,
        timeout: float = 20.0,
    ) -> None:
        self._api_key = (api_key or license_key()).strip()
        self.base_url = (base_url or os.getenv("SUPAFONE_LABS_API_BASE") or DEFAULT_API_BASE).rstrip("/")
        self._client = client
        self.timeout = timeout

    async def complete(
        self, messages: list[dict[str, str]], model: str | None = None, **kwargs: Any
    ) -> str:
        if not self._api_key:
            raise TierError(
                "HostedLLMProvider needs a SUPAFONE_LABS_API_KEY (pro tier). "
                "On the free tier use your own keys: AnthropicProvider or OpenAIProvider."
            )
        client = self._client
        owns_client = client is None
        if owns_client:
            try:
                import httpx
            except ImportError as exc:  # pragma: no cover - exercised only without the extra
                raise RuntimeError(
                    "HostedLLMProvider requires the 'http' extra: pip install supafone-labs[http]"
                ) from exc
            client = httpx.AsyncClient(timeout=self.timeout)
        try:
            resp = await client.post(
                f"{self.base_url}/oracle/complete",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "messages": messages,
                    "model": model,
                    "max_tokens": kwargs.get("max_tokens", 1024),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return str(data.get("text") or data.get("completion") or "")
        finally:
            if owns_client:
                await client.aclose()
