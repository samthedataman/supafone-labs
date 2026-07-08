"""Shared SupafoneLabs data model. Reuses the runtime's RuntimeDecision for injection."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from supafone_labs.runtime.core.decision import RuntimeDecision


SUPPORTED_LANGUAGE_NAMES = {
    "ar": "Arabic",
    "bg": "Bulgarian",
    "zh": "Chinese",
    "cs": "Czech",
    "da": "Danish",
    "nl": "Dutch",
    "en": "English",
    "fi": "Finnish",
    "fr": "French",
    "de": "German",
    "el": "Greek",
    "hi": "Hindi",
    "hu": "Hungarian",
    "it": "Italian",
    "ja": "Japanese",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "es": "Spanish",
    "sv": "Swedish",
    "ta": "Tamil",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "vi": "Vietnamese",
}

_LANGUAGE_NAME_TO_CODE = {
    name.lower(): code for code, name in SUPPORTED_LANGUAGE_NAMES.items()
}
_LANGUAGE_NAME_TO_CODE.update(
    {
        "arabic": "ar",
        "bulgarian": "bg",
        "mandarin": "zh",
        "chinese": "zh",
        "czech": "cs",
        "danish": "da",
        "dutch": "nl",
        "english": "en",
        "ingles": "en",
        "ingl\u00e9s": "en",
        "finnish": "fi",
        "french": "fr",
        "german": "de",
        "greek": "el",
        "hindi": "hi",
        "hungarian": "hu",
        "italian": "it",
        "japanese": "ja",
        "polish": "pl",
        "portuguese": "pt",
        "romanian": "ro",
        "russian": "ru",
        "slovak": "sk",
        "spanish": "es",
        "espanol": "es",
        "espa\u00f1ol": "es",
        "swedish": "sv",
        "tamil": "ta",
        "turkish": "tr",
        "ukrainian": "uk",
        "vietnamese": "vi",
    }
)


def normalize_language_code(value: str) -> str:
    """Normalize common language labels into compact codes."""
    text = str(value or "").strip().lower().replace("_", "-")
    if not text:
        return "unknown"
    if text in {"unknown", "und", "auto", "multi", "multilingual"}:
        return "unknown"
    if text in _LANGUAGE_NAME_TO_CODE:
        return _LANGUAGE_NAME_TO_CODE[text]
    primary = text.split("-", 1)[0]
    if primary in SUPPORTED_LANGUAGE_NAMES:
        return primary
    return text


def is_spanish_language(value: str) -> bool:
    return normalize_language_code(value) == "es"


def is_english_language(value: str) -> bool:
    return normalize_language_code(value) == "en"


_SPANISH_ITEM_TRANSLATIONS = {
    "dont quote fees": "No menciones honorarios.",
    "do not quote fees": "No menciones honorarios.",
    "no legal advice": "No des asesoria legal.",
    "acknowledge injury/distress before logistics": (
        "Reconoce la lesion o angustia antes de la logistica."
    ),
    "no clinical advice": "No des consejos clinicos.",
    "protect phi - verify identity before sharing": (
        "Protege la informacion privada y verifica identidad antes de compartir datos."
    ),
    "escalate emergencies to 911 immediately": "Escala emergencias al 911 de inmediato.",
    "lead with value": "Empieza con valor.",
    "respect do-not-call / opt-out signals": "Respeta senales de no llamar o cancelar.",
    "confirm you understood before resolving": "Confirma que entendiste antes de resolver.",
}


def _spanish_item(value: str) -> str:
    key = (
        str(value or "")
        .strip()
        .lower()
        .replace("'", "")
        .replace("\u2014", "-")
    )
    key = " ".join(key.split())
    return _SPANISH_ITEM_TRANSLATIONS.get(key, str(value or "").strip())


class DirectiveKind(str, Enum):
    """What kind of coaching a directive carries."""

    EMPATHY = "empathy"
    TACTICAL = "tactical"
    GUARDRAIL = "guardrail"
    MIXED = "mixed"


class BeliefState(BaseModel):
    """The oracle's structured, continuously-revised read of the caller."""

    model_config = {"extra": "ignore"}

    caller_identity: str = "unknown"
    case_type: str = "unknown"
    emotional_state: str = "neutral"
    intent: str = "unknown"
    language: str = "unknown"
    urgency: float = 0.0
    confidence: float = 0.0
    surface_facts: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
    notes: str = ""


class Directive(BaseModel):
    """A silent coaching directive the live agent reads but never speaks."""

    model_config = {"extra": "ignore"}

    empathy_directive: str = ""
    tactical_directive: str = ""
    surface_facts: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
    language: str = ""
    confidence: float = 0.0
    kind: DirectiveKind = DirectiveKind.MIXED

    def composed_text(self) -> str:
        """Render the directive into a single hidden-instruction string for injection."""
        language = normalize_language_code(self.language)
        english = language in {"", "unknown", "en"}
        spanish = language == "es"
        parts: list[str] = []
        if self.empathy_directive:
            parts.append(self.empathy_directive.strip())
        if self.tactical_directive:
            parts.append(self.tactical_directive.strip())
        if self.surface_facts:
            facts = [_spanish_item(item) for item in self.surface_facts] if spanish else self.surface_facts
            if english:
                parts.append("Know: " + "; ".join(facts))
            elif spanish:
                parts.append("Ten presente: " + "; ".join(facts))
            else:
                parts.append("; ".join(facts))
        if self.guardrails:
            guardrails = (
                [_spanish_item(item) for item in self.guardrails] if spanish else self.guardrails
            )
            if english:
                parts.append("Do not: " + "; ".join(guardrails))
            elif spanish:
                parts.append("No hagas: " + "; ".join(guardrails))
            else:
                parts.append("; ".join(guardrails))
        return " ".join(p for p in parts if p).strip()


def directive_to_decision(
    directive: Optional[Directive], threshold: float = 0.5
) -> Optional[RuntimeDecision]:
    """Map a confident directive to a runtime inject_hidden_instruction decision, else None."""
    if directive is None:
        return None
    text = directive.composed_text()
    if not text or directive.confidence < threshold:
        return None
    return RuntimeDecision.inject_hidden_instruction(text)
