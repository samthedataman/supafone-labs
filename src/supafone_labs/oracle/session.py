"""OracleSession — the off-hot-path second mind. Time-bounded, degrade-safe."""
from __future__ import annotations

import asyncio
from typing import Optional

from supafone_labs.config import Settings, get_settings
from supafone_labs.llm.base import LLMProvider
from supafone_labs.llm.registry import get_default_provider
from supafone_labs.oracle.belief_state import BeliefStateEngine
from supafone_labs.oracle.directive import DirectiveGenerator, should_emit
from supafone_labs.runtime.core.state import RuntimeState
from supafone_labs.types import BeliefState, Directive


class OracleSession:
    """Runs belief -> directive off the hot path and buffers the latest directive per session.

    `observe` is wrapped in a timeout and never raises — a stalled or failing oracle simply
    yields no directive, leaving the host conversation untouched.
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        config: Optional[Settings] = None,
        guardrails: Optional[list[str]] = None,
        *,
        model: Optional[str] = None,
        belief_prompt: Optional[str] = None,
        directive_prompt: Optional[str] = None,
        instructions: Optional[str] = None,
    ) -> None:
        self.config = config or get_settings()
        if model:  # pick your second-brain model without touching env config
            self.config = self.config.model_copy(update={"oracle_model": model})
        self.provider = provider or get_default_provider()
        self.belief_engine = BeliefStateEngine(
            self.provider, self.config, system_prompt=belief_prompt, extra_instructions=instructions
        )
        self.directive_gen = DirectiveGenerator(
            self.provider, self.config, system_prompt=directive_prompt, extra_instructions=instructions
        )
        self.guardrails = guardrails or []
        self.last_belief: Optional[BeliefState] = None
        self._buffer: dict[str, Directive] = {}
        self._feedback: list[object] = []

    async def observe(self, state: RuntimeState) -> Optional[Directive]:
        """Compute a directive for this turn; returns None on timeout/error (degrade-safe)."""
        try:
            return await asyncio.wait_for(
                self._observe(state), timeout=self.config.oracle_timeout_seconds
            )
        except Exception:
            return None

    async def _observe(self, state: RuntimeState) -> Optional[Directive]:
        belief = await self.belief_engine.update(state, self.last_belief)
        self.last_belief = belief
        directive = await self.directive_gen.generate(belief, state, self.guardrails)
        if should_emit(directive, self.config.confidence_threshold):
            self._buffer[state.session_id] = directive
            return directive
        return None

    def drain(self, session_id: str) -> Optional[Directive]:
        """Pop the buffered directive for a session (used by the sync OracleWorkflow)."""
        return self._buffer.pop(session_id, None)

    def feedback(self, reward: object) -> None:
        """Record an outcome signal (consumed later by online reinjection)."""
        self._feedback.append(reward)
