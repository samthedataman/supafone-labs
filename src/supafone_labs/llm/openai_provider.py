"""LLMProvider backed by the OpenAI SDK (imported lazily)."""
from __future__ import annotations

import os
from typing import Any


class OpenAIProvider:
    """Chat-completions provider using the OpenAI SDK; imported only when used.

    `base_url` makes this serve any OpenAI-compatible vendor — xAI's Grok API
    is `OpenAIProvider(base_url="https://api.x.ai/v1", api_key=XAI_API_KEY)`.
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model or "gpt-4o-mini"
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url

    async def complete(
        self, messages: list[dict[str, str]], model: str | None = None, **kwargs: Any
    ) -> str:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "OpenAIProvider requires the 'openai' extra: pip install supafone-labs[openai]"
            ) from exc

        client = AsyncOpenAI(api_key=self._api_key, base_url=self.base_url)
        resp = await client.chat.completions.create(
            model=model or self.model,
            messages=[{"role": m.get("role", "user"), "content": m["content"]} for m in messages],
            max_tokens=kwargs.get("max_tokens", 1024),
        )
        return resp.choices[0].message.content or ""
