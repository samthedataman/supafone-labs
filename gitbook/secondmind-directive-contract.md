# Programmable SecondMind Directives

SecondMind can return inspectable structured guidance instead of one opaque
whisper. Developers control the output contract while Supafone continues to
observe the call, infer the current belief state, and apply the confidence gate.

```json
{
  "empathy_directive": "Slow down and acknowledge that the caller is worried.",
  "tactical_directive": "Confirm the preferred callback time before closing.",
  "surface_facts": ["The caller requested a callback after 5 PM."],
  "guardrails": ["Do not claim the callback is scheduled until a tool confirms it."],
  "language": "en",
  "confidence": 0.86,
  "kind": "mixed"
}
```

## What Developers Control

| Control | Effect |
|---|---|
| `enabled` | Include or deterministically clear a field |
| `instructions` | Give field-specific generation requirements |
| `max_chars` / `maxChars` | Bound a directive string after generation |
| `max_items` / `maxItems` | Bound a fact or guardrail list |
| `item_max_chars` / `itemMaxChars` | Bound each list item |
| `language_mode` / `languageMode` | Follow the caller, trust the model, or force one language |
| `allowed_kinds` / `allowedKinds` | Suppress kinds the application does not accept |
| `confidence_threshold` / `confidenceThreshold` | Emit nothing below the configured evidence gate |
| `operator_guardrails` / `operatorGuardrails` | Add application-specific standing rules |
| transform callback | Revise or suppress the final directive in local SDK code |

The contract is applied in the model prompt and enforced again in code. A model
cannot ignore a disabled field, exceed a configured bound, or bypass the
confidence and kind gates.

## Python

```python
from supafone_labs import DirectiveContract, supercharge

brain = supercharge(
    my_agent,
    scenario="legal_intake",
    directive_contract=DirectiveContract(
        empathy_directive={
            "instructions": "Acknowledge emotion in one calm sentence.",
            "max_chars": 120,
        },
        tactical_directive={
            "instructions": "Name exactly one next operational action.",
            "max_chars": 140,
        },
        surface_facts={"max_items": 3},
        guardrails={"max_items": 4},
        language_mode="caller",
        confidence_threshold=0.8,
        operator_guardrails=[
            "Never claim a callback is booked until the scheduling tool confirms it."
        ],
    ),
)
```

For local code that needs final control, use a sync or async transform. Returning
`None` suppresses the directive:

```python
async def approve(directive, belief, state):
    if belief.intent == "unknown":
        return None
    return directive.model_copy(
        update={"tactical_directive": "Escalate this turn to the application router."}
    )

brain = supercharge(my_agent, directive_transform=approve)
```

## TypeScript

```ts
const directive = await supafone.whisperStructured(transcript, {
  directiveContract: {
    empathyDirective: {
      instructions: "Acknowledge emotion in one calm sentence.",
      maxChars: 120,
    },
    tacticalDirective: {
      instructions: "Name exactly one next operational action.",
      maxChars: 140,
    },
    surfaceFacts: { maxItems: 3 },
    guardrails: { maxItems: 4 },
    languageMode: "caller",
    confidenceThreshold: 0.8,
    operatorGuardrails: [
      "Never claim a callback is booked until the scheduling tool confirms it."
    ],
  },
  transform: (candidate) =>
    candidate.surface_facts.length ? candidate : null,
});
```

`whisper()` remains the backward-compatible one-string convenience method.
`whisperStructured()` and its `directive()` alias return the structured object
or `null` when guidance is not justified.

## Safety Boundary

Developer controls govern generated coaching. They do not erase platform or
scenario safety requirements. Standing safety rules remain in the reasoning
prompt even when generated `guardrails` are hidden, and a callback failure
degrades to no guidance rather than affecting the live call.

