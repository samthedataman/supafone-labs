"""DirectiveGenerator — the oracle's coaching core (belief -> silent directive)."""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

from supafone_labs._json import loads_tolerant
from supafone_labs.config import Settings, get_settings
from supafone_labs.llm.base import LLMProvider
from supafone_labs.runtime.core.state import RuntimeState
from supafone_labs.types import (
    SUPPORTED_LANGUAGE_NAMES,
    BeliefState,
    Directive,
    is_english_language,
    normalize_language_code,
)

DIRECTIVE_SYSTEM = (
    "You are the coaching core of a 'second mind' for a live voice agent. Given the caller belief "
    "state, produce a single silent coaching DIRECTIVE the agent will read but never speak aloud. "
    "Return ONLY a JSON object with keys: empathy_directive (string), tactical_directive (string), "
    "surface_facts (array), guardrails (array), language (short code like en, es, or unknown), "
    "confidence (0-1 float), kind (one of: empathy, tactical, guardrail, mixed). "
    "Mirror the caller's language for every human-readable value when the transcript is clearly "
    "not English. Be silent (low confidence) if unsure. No prose — JSON only."
)

_SPANISH_MARKERS = frozenset(
    {
        "abogado",
        "accidente",
        "ahora",
        "ayer",
        "ayuda",
        "buenas",
        "buenos",
        "choque",
        "cita",
        "como",
        "con",
        "cuello",
        "de",
        "del",
        "dolor",
        "duele",
        "el",
        "en",
        "espanol",
        "estoy",
        "fue",
        "gracias",
        "habla",
        "hablo",
        "hola",
        "la",
        "lastimado",
        "lesion",
        "llamar",
        "llamo",
        "me",
        "mi",
        "necesito",
        "para",
        "pero",
        "porque",
        "que",
        "quiero",
        "si",
        "telefono",
        "tengo",
        "un",
        "una",
    }
)


def should_emit(directive: Optional[Directive], threshold: float = 0.5) -> bool:
    """Confidence gate: only emit a directive with real content above the threshold."""
    return bool(directive and directive.composed_text() and directive.confidence >= threshold)


def _ascii_tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.findall(r"[a-z]+", ascii_text.lower())


def _format_recent_transcript(state: RuntimeState, limit: int = 12) -> str:
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


def _infer_language(state: RuntimeState, belief: BeliefState) -> str:
    belief_language = normalize_language_code(getattr(belief, "language", ""))
    if belief_language != "unknown":
        return belief_language

    turn_languages = [
        normalize_language_code(getattr(turn, "language", ""))
        for turn in state.transcript[-12:]
        if str(getattr(turn, "actor", "") or "").strip().lower() == "caller"
    ]
    for language in reversed(turn_languages):
        if language and language != "unknown":
            return language

    caller_text = " ".join(
        str(turn.text or "")
        for turn in state.transcript[-12:]
        if str(turn.actor or "").strip().lower() == "caller"
    )
    tokens = _ascii_tokens(caller_text)
    if not tokens:
        return "unknown"
    if "espanol" in tokens:
        return "es"
    spanish_hits = sum(1 for token in tokens if token in _SPANISH_MARKERS)
    return "es" if spanish_hits >= 3 else "unknown"


def _language_rule(language_code: str) -> str:
    language = normalize_language_code(language_code)
    name = SUPPORTED_LANGUAGE_NAMES.get(language, language_code or "the caller's language")
    return (
        f"Language rule: The caller appears to be speaking {name} ({language}). "
        f"Return every human-readable JSON value in natural {name}: empathy_directive, "
        "tactical_directive, surface_facts, and guardrails. Keep the coaching short. "
        "Do not tell the agent to switch to English."
    )


class DirectiveGenerator:
    """Produces a confidence-gated Directive from a BeliefState. Degrade-safe."""

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
        self.system_prompt = system_prompt or DIRECTIVE_SYSTEM
        if extra_instructions:
            self.system_prompt = f"{self.system_prompt}\n\nOperator instructions: {extra_instructions}"

    async def generate(
        self,
        belief: BeliefState,
        state: RuntimeState,
        guardrails: Optional[list[str]] = None,
    ) -> Directive:
        """Return a Directive; empty (confidence 0) on any failure so callers stay safe."""
        try:
            detected_language = _infer_language(state, belief)
            system_prompt = self.system_prompt
            if detected_language != "unknown" and not is_english_language(detected_language):
                system_prompt = f"{self.system_prompt}\n\n{_language_rule(detected_language)}"
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Belief state:\n{belief.model_dump_json(indent=2)}\n\n"
                        f"Detected language: {detected_language}\n\n"
                        f"Recent transcript:\n{_format_recent_transcript(state)}\n\n"
                        f"Standing guardrails to honor: {guardrails or []}\n\n"
                        "Return the coaching directive as JSON."
                    ),
                },
            ]
            raw = await self.provider.complete(messages, model=self.config.oracle_model)
            data = loads_tolerant(raw)
            if not data:
                return Directive()
            directive = Directive.model_validate(data)
            language = normalize_language_code(
                detected_language
                if detected_language != "unknown"
                else directive.language or getattr(belief, "language", "")
            )
            if language != "unknown":
                directive.language = language
            if guardrails:
                # The standing guardrails are English operator controls. For
                # non-English callers, keep them in the prompt but do not append
                # untranslated English text to the hidden instruction.
                if language in {"unknown", "en"}:
                    directive.guardrails = list(dict.fromkeys([*directive.guardrails, *guardrails]))
            return directive
        except Exception:
            return Directive()
