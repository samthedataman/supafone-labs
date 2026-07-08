"""Pick your second-brain model + customize the oracle's prompts.

    pip install supafone-labs[all]
    python custom_model_and_prompts.py       # runs offline on the fake provider
"""
import asyncio

import supafone_labs


async def main() -> None:
    # Live model discovery — never hardcode a list (queries every vendor whose
    # key you hold; cached hourly; static fallback offline):
    models = await supafone_labs.discover_oracle_models()
    print("available:", {k: v[:3] for k, v in models.items()})

    brain = supafone_labs.SupafoneLabs(
        provider="ultravox",
        # Provider is inferred from the model id — Anthropic here; use
        # "gpt-4.1-mini" (OpenAI), "grok-4-fast" (xAI), or
        # "supafone-labs-oracle" (hosted, pinned server-side, never deprecates).
        oracle_model="claude-sonnet-4-6",
        llm="fake",  # drop this line to use the real model above
        # Operator guidance appended to BOTH oracle cores:
        oracle_instructions=(
            "Coach for a bilingual personal-injury intake desk. Empathy before "
            "logistics. Never quote fees. Escalate anything medical to a human."
        ),
        mode="return",
    )

    result = await brain.observe({
        "type": "transcript", "speaker": "caller", "final": True, "call_id": "demo",
        "text": "I was rear-ended at a red light yesterday and my neck hurts.",
    })
    print("belief:", result.belief.emotional_state, "/", result.belief.intent)
    print("whisper:", result.directive.composed_text())
    print("native action:", result.actions[0].kind if result.actions else None)


asyncio.run(main())
