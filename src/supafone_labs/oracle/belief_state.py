"""BeliefStateEngine — the oracle's perception core (LLM over the canonical transcript)."""
from __future__ import annotations

from typing import Optional

from supafone_labs._json import loads_tolerant
from supafone_labs.config import Settings, get_settings
from supafone_labs.llm.base import LLMProvider
from supafone_labs.runtime.core.state import RuntimeState
from supafone_labs.types import BeliefState

BELIEF_SYSTEM = (
    "You are the perception core of a 'second mind' that rides alongside a live voice agent. "
    "Maintain a structured BELIEF STATE about the caller from the conversation so far. "
    "Return ONLY a JSON object with keys: caller_identity, case_type, emotional_state, intent, "
    "language (short code like en, es, or unknown), urgency (0-1 float), confidence (0-1 float), "
    "surface_facts (array of short strings), guardrails (array of short strings), notes. "
    "If the caller is speaking Spanish, set language to es. No prose — JSON only."
)


def _format_transcript(state: RuntimeState, limit: int = 30) -> str:
    turns = state.transcript[-limit:]
    if not turns:
        return "(no turns yet)"
    lines: list[str] = []
    for turn in turns:
        if not turn.text:
            continue
        language = f" [{turn.language}]" if getattr(turn, "language", "") else ""
        lines.append(f"{turn.actor}{language}: {turn.text}")
    return "\n".join(lines)


class BeliefStateEngine:
    """Turns the runtime's RuntimeState into a revised BeliefState via the LLM. Degrade-safe."""

    def __init__(
        self,
        provider: LLMProvider,
        config: Optional[Settings] = None,
        *,
        system_prompt: Optional[str] = None,
        extra_instructions: Optional[str] = None,
    ) -> None:
        self.provider = provider
        self.config = config or get_settings()
        self.system_prompt = system_prompt or BELIEF_SYSTEM
        if extra_instructions:
            self.system_prompt = f"{self.system_prompt}\n\nOperator instructions: {extra_instructions}"

    async def update(
        self, state: RuntimeState, prior: Optional[BeliefState] = None
    ) -> BeliefState:
        """Return an updated belief; falls back to `prior` (or empty) on any failure."""
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Conversation so far:\n{_format_transcript(state)}\n\n"
                        "Return the updated belief state as JSON."
                    ),
                },
            ]
            raw = await self.provider.complete(messages, model=self.config.oracle_model)
            data = loads_tolerant(raw)
            if not data:
                return prior or BeliefState()
            return BeliefState.model_validate(data)
        except Exception:
            return prior or BeliefState()
