"""Proves the Ultravox path works end to end with the offline fake provider."""

from supafone_labs import SupafoneLabs, supercharge
from supafone_labs.llm import FakeLLMProvider
from supafone_labs.oracle.session import OracleSession
from supafone_labs.runtime.adapters import UltravoxAdapter
from supafone_labs.runtime.core.state import build_initial_state
from supafone_labs.types import Directive, directive_to_decision


async def test_supercharge_ultravox_end_to_end(ultravox_event):
    oracle = OracleSession(provider=FakeLLMProvider())
    brain = SupafoneLabs(provider="ultravox", oracle=oracle, mode="return")

    result = await brain.observe(ultravox_event)

    assert result.belief is not None
    assert result.belief.case_type == "auto_accident"
    assert result.directive is not None and result.directive.composed_text()
    assert result.decision is not None
    assert result.actions, "expected a compiled Ultravox action"
    action = result.actions[0]
    assert action.provider == "ultravox"
    assert action.kind == "inject_message"
    assert "<instruction>" in action.payload["message"]


async def test_directive_compiles_via_ultravox_adapter():
    directive = Directive(
        empathy_directive="Slow down and acknowledge the pain.",
        tactical_directive="Secure the consult now.",
        confidence=0.9,
    )
    decision = directive_to_decision(directive)
    assert decision is not None
    state = build_initial_state(provider="ultravox", session_id="c1")
    actions = await UltravoxAdapter().compile(decision, state)
    assert actions and actions[0].kind == "inject_message"
    assert "Slow down" in actions[0].payload["message"]


def test_low_confidence_is_suppressed():
    directive = Directive(empathy_directive="maybe", confidence=0.1)
    assert directive_to_decision(directive, threshold=0.5) is None


async def test_apply_mode_injects_into_agent(ultravox_event):
    class Agent:
        provider_name = "ultravox"

        def __init__(self):
            self.got = []

        def inject(self, actions):
            self.got.extend(actions)

    agent = Agent()
    brain = supercharge(agent, scenario="legal_intake")  # mode defaults to "apply"
    result = await brain.observe(ultravox_event)
    assert result.injected is True
    assert agent.got and agent.got[0].kind == "inject_message"


async def test_degrade_safe_when_provider_raises(ultravox_event):
    class Boom:
        async def complete(self, *args, **kwargs):
            raise RuntimeError("oracle exploded")

    brain = SupafoneLabs(provider="ultravox", oracle=OracleSession(provider=Boom()), mode="return")
    result = await brain.observe(ultravox_event)
    # No crash, no directive — the call would proceed normally.
    assert result.directive is None
    assert result.actions == []
