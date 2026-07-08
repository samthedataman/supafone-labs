"""Shared HTTP plumbing for the real TTS backends (lazy httpx, injectable client)."""
from __future__ import annotations

from typing import Any


class HttpTTSBase:
    """Owns the httpx client lifecycle so each backend is a single _request()."""

    provider_name = "http"

    def __init__(self, client: Any = None, timeout: float = 30.0) -> None:
        self._client = client
        self.timeout = timeout

    async def _post_bytes(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
        params: dict[str, str] | None = None,
    ) -> bytes:
        client = self._client
        owns_client = client is None
        if owns_client:
            try:
                import httpx
            except ImportError as exc:  # pragma: no cover - exercised only without the extra
                raise RuntimeError(
                    f"{type(self).__name__} requires the 'http' extra: pip install supafone-labs[http]"
                ) from exc
            client = httpx.AsyncClient(timeout=self.timeout)
        try:
            resp = await client.post(url, headers=headers, json=json, params=params)
            resp.raise_for_status()
            return resp.content
        finally:
            if owns_client:
                await client.aclose()
