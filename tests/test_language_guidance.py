from supafone_labs.oracle.session import OracleSession
from supafone_labs.runtime.core.events import EventTypes, make_event
from supafone_labs.runtime.core.state import apply_events, build_initial_state
from supafone_labs.types import Directive


class CapturingProvider:
    def __init__(self) -> None:
        self.messages = []

    async def complete(self, messages, model=None, **kwargs):
        self.messages.append(messages)
        prompt = " ".join((message.get("content") or "") for message in messages).lower()
        if "coaching directive" not in prompt:
            return (
                '{"caller_identity":"new_lead","case_type":"unknown",'
                '"emotional_state":"confused","intent":"needs_help","language":"fr",'
                '"urgency":0.3,"confidence":0.8,"surface_facts":["appel confus"],'
                '"guardrails":[],"notes":"French caller."}'
            )
        return (
            '{"empathy_directive":"Ralentissez et rassurez la personne.",'
            '"tactical_directive":"Posez une seule question claire.",'
            '"surface_facts":["La personne est confuse"],'
            '"guardrails":["Ne donnez pas de conseils juridiques"],'
            '"language":"fr","confidence":0.9,"kind":"mixed"}'
        )


async def test_directive_mirrors_detected_non_english_language_without_english_guardrail_leak():
    provider = CapturingProvider()
    oracle = OracleSession(provider=provider, guardrails=["Don't quote fees", "No legal advice"])
    state = build_initial_state(provider="ultravox", session_id="call-fr")
    state = apply_events(
        [
            make_event(
                EventTypes.CALLER_TRANSCRIPT_FINAL,
                session_id="call-fr",
                provider="ultravox",
                actor="caller",
                text="Bonjour, j'ai besoin d'aide.",
                data={"language": "fr"},
            )
        ],
        state,
    )

    directive = await oracle.observe(state)

    assert directive is not None
    rendered = directive.composed_text()
    assert "Ralentissez" in rendered
    assert "Don't quote fees" not in rendered
    assert "No legal advice" not in rendered
    assert "Do not:" not in rendered

    directive_prompt = " ".join(
        message.get("content") or "" for message in provider.messages[-1]
    )
    assert "French (fr)" in directive_prompt


def test_spanish_directive_uses_spanish_labels_not_english_labels():
    directive = Directive(
        empathy_directive="Reconozca el dolor antes de pedir datos.",
        tactical_directive="Haga una sola pregunta sencilla.",
        surface_facts=["La persona llama por un accidente"],
        guardrails=["No legal advice"],
        language="es",
        confidence=0.9,
    )

    rendered = directive.composed_text()

    assert "Ten presente:" in rendered
    assert "No hagas:" in rendered
    assert "Do not:" not in rendered
    assert "No des asesoria legal." in rendered
