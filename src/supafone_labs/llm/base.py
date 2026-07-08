"""LLM provider contract + a deterministic fake + a lazy Anthropic provider."""
from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

_DEFAULT_BELIEF = (
    '{"caller_identity":"new_lead","case_type":"auto_accident","emotional_state":"distressed",'
    '"intent":"fresh_injury_high_signup","urgency":0.8,"confidence":0.82,'
    '"surface_facts":["Rear-ended at a red light yesterday","Neck and back pain"],'
    '"guardrails":["Don\'t quote fees","No legal advice"],'
    '"notes":"Fresh MVA, liability likely clear, high signup intent."}'
)

_DEFAULT_DIRECTIVE = (
    '{"empathy_directive":"The caller is in pain and frightened — slow down and acknowledge the '
    'injury before any logistics.","tactical_directive":"Fresh rear-end collision, liability likely '
    'clear, high intent. Secure the consultation now; capture date of loss and injuries.",'
    '"surface_facts":["Rear-ended yesterday at a red light","Neck/back pain"],'
    '"guardrails":["Don\'t quote fees","No legal advice"],"confidence":0.82,"kind":"mixed"}'
)


@runtime_checkable
class LLMProvider(Protocol):
    """Anything that can complete a chat-style message list into text."""

    async def complete(
        self, messages: list[dict[str, str]], model: str | None = None, **kwargs: Any
    ) -> str: ...


class FakeLLMProvider:
    """Deterministic, network-free provider for tests and zero-key demos.

    Branches on whether the prompt is asking for a belief state or a directive so the
    full oracle pipeline produces a real, inspectable result with no API key.
    """

    def __init__(self, belief_json: str | None = None, directive_json: str | None = None) -> None:
        self.belief_json = belief_json or _DEFAULT_BELIEF
        self.directive_json = directive_json or _DEFAULT_DIRECTIVE

    async def complete(
        self, messages: list[dict[str, str]], model: str | None = None, **kwargs: Any
    ) -> str:
        text = " ".join((m.get("content") or "") for m in messages).lower()
        if "directive" in text:
            return self.directive_json
        if "belief" in text:
            return self.belief_json
        return "{}"


class AnthropicProvider:
    """LLMProvider backed by the Anthropic SDK (imported lazily)."""

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    async def complete(
        self, messages: list[dict[str, str]], model: str | None = None, **kwargs: Any
    ) -> str:
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise RuntimeError(
                "AnthropicProvider requires the 'anthropic' extra: pip install supafone-labs[anthropic]"
            ) from exc

        client = AsyncAnthropic(api_key=self._api_key)
        system = "\n".join(m["content"] for m in messages if m.get("role") == "system")
        chat = [
            {"role": m.get("role", "user"), "content": m["content"]}
            for m in messages
            if m.get("role") != "system"
        ]
        resp = await client.messages.create(
            model=model or self.model or "claude-haiku-4-5-20251001",
            max_tokens=kwargs.get("max_tokens", 1024),
            system=system or "You are a helpful assistant.",
            messages=chat or [{"role": "user", "content": ""}],
        )
        return "".join(
            getattr(block, "text", "") for block in resp.content if getattr(block, "type", None) == "text"
        )
