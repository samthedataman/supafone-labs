"""Ultravox end-to-end: one line to supercharge an agent, run with no API key.

    python examples/ultravox_end_to_end.py
"""
import asyncio

import supafone_labs


class FakeUltravoxAgent:
    """Stand-in for a real Ultravox agent. provider_name drives auto-detection;
    inject() is what SupafoneLabs calls to silently whisper guidance to the agent."""

    provider_name = "ultravox"

    def __init__(self) -> None:
        self.injected: list[str] = []

    def inject(self, actions) -> None:
        for action in actions:
            self.injected.append(action.payload.get("message", ""))


async def main() -> None:
    agent = FakeUltravoxAgent()

    # The one line. Provider auto-detected as "ultravox"; runs on the offline fake LLM.
    brain = supafone_labs.supercharge(agent, scenario="legal_intake")

    # A real Ultravox transcript webhook event for an incoming caller.
    event = {
        "type": "transcript",
        "speaker": "caller",
        "text": "I was rear-ended at a red light yesterday and my neck really hurts.",
        "final": True,
        "call_id": "call_demo_1",
    }

    result = await brain.observe(event)

    print("=== Belief ===")
    print(result.belief.model_dump_json(indent=2) if result.belief else "(none)")
    print("\n=== Silent directive whispered to the agent ===")
    print(result.directive.composed_text() if result.directive else "(suppressed)")
    print("\n=== Compiled Ultravox control action ===")
    for action in result.actions:
        print(f"{action.provider}.{action.kind}: {action.payload}")
    print(f"\nInjected into agent: {result.injected}")
    print(f"Agent received: {agent.injected}")


if __name__ == "__main__":
    asyncio.run(main())
