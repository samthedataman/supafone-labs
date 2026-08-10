from __future__ import annotations

from supafone_labs.oracle.session import OracleSession
from supafone_labs.runtime.core.events import EventTypes, make_event
from supafone_labs.runtime.core.state import apply_events, build_initial_state


class ContractProvider:
    def __init__(
        self,
        *,
        kind: str = "mixed",
        confidence: float = 0.9,
        directive_language: str = "en",
    ) -> None:
        self.kind = kind
        self.confidence = confidence
        self.directive_language = directive_language
        self.messages: list[list[dict]] = []

    async def complete(self, messages, model=None, **kwargs):
        self.messages.append(messages)
        prompt = " ".join(str(message.get("content") or "") for message in messages)
        if "Return the coaching directive as JSON" not in prompt:
            return (
                '{"caller_identity":"known","case_type":"callback",'
                '"emotional_state":"worried","intent":"request_callback","language":"en",'
                '"urgency":0.4,"confidence":0.9,"surface_facts":["after 5 PM"],'
                '"guardrails":[],"notes":"Caller requested a callback."}'
            )
        return (
            '{"empathy_directive":"Acknowledge that the caller is worried before moving on.",'
            '"tactical_directive":"Confirm the preferred callback time before closing.",'
            '"surface_facts":["Callback requested after 5 PM","Caller sounded worried"],'
            f'"guardrails":["Do not promise scheduling"],"language":"{self.directive_language}",'
            f'"confidence":{self.confidence},"kind":"{self.kind}"}}'
        )


def state_for_call():
    state = build_initial_state(provider="ultravox", session_id="call-contract")
    return apply_events(
        [
            make_event(
                EventTypes.CALLER_TRANSCRIPT_FINAL,
                session_id="call-contract",
                provider="ultravox",
                actor="caller",
                text="Please call me after five. I am worried about this.",
                data={"language": "en"},
            )
        ],
        state,
    )


async def test_directive_contract_controls_and_enforces_every_output_field():
    provider = ContractProvider()
    oracle = OracleSession(
        provider=provider,
        directive_contract={
            "empathy_directive": {"enabled": False},
            "tactical_directive": {
                "instructions": "Use one direct operational instruction.",
                "max_chars": 18,
            },
            "surface_facts": {"max_items": 1, "item_max_chars": 12},
            "guardrails": {"enabled": False},
            "language_mode": "fixed",
            "fixed_language": "es",
            "allowed_kinds": ["mixed"],
            "confidence_threshold": 0.85,
            "operator_guardrails": ["Never claim a callback is booked without tool confirmation"],
        },
    )

    directive = await oracle.observe(state_for_call())

    assert directive is not None
    assert directive.empathy_directive == ""
    assert directive.tactical_directive == "Confirm the prefer"
    assert directive.surface_facts == ["Callback req"]
    assert directive.guardrails == []
    assert directive.language == "es"
    assert oracle.confidence_threshold == 0.85
    prompt = "\n".join(
        str(message.get("content") or "") for message in provider.messages[-1]
    )
    assert "Developer directive contract" in prompt
    assert "Use one direct operational instruction" in prompt
    assert "Never claim a callback is booked" in prompt


async def test_directive_contract_suppresses_disallowed_kind():
    oracle = OracleSession(
        provider=ContractProvider(kind="empathy"),
        directive_contract={"allowed_kinds": ["tactical"]},
    )

    assert await oracle.observe(state_for_call()) is None


async def test_directive_contract_can_trust_model_language_instead_of_detection():
    oracle = OracleSession(
        provider=ContractProvider(directive_language="fr"),
        directive_contract={"language_mode": "model"},
    )

    directive = await oracle.observe(state_for_call())

    assert directive is not None
    assert directive.language == "fr"


async def test_directive_transform_has_final_say_and_can_suppress():
    observed = []

    async def revise(directive, belief, state):
        observed.append((belief.intent, state.session_id))
        return directive.model_copy(
            update={"tactical_directive": "Use the developer-selected action.", "confidence": 0.99}
        )

    oracle = OracleSession(provider=ContractProvider(), directive_transform=revise)
    directive = await oracle.observe(state_for_call())

    assert directive is not None
    assert directive.tactical_directive == "Use the developer-selected action."
    assert observed == [("request_callback", "call-contract")]

    suppressing = OracleSession(
        provider=ContractProvider(),
        directive_transform=lambda directive, belief, state: None,
    )
    assert await suppressing.observe(state_for_call()) is None
