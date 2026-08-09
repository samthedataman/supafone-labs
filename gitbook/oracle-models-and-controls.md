# Oracle Models and Supervisor Controls

The Oracle is the reasoning model behind Voice Watcher. It is independent from
the model speaking on the call: an Ultravox, Vapi, Retell, OpenAI Realtime,
Grok, or custom agent can be supervised by a different model without changing
the caller-facing runtime.

## Supafone-managed Oracle

Customers should configure a stable Supafone alias rather than coupling their
agent to a vendor model ID:

| Public alias | Current managed model | Intended work |
| --- | --- | --- |
| `supafone-labs-oracle` | Anthropic Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) | Fast live belief updates and bounded silent directives |
| `supafone-labs-oracle-pro` | Anthropic Claude Sonnet 4.6 | Heavier QA, critique, scoring, and optimization |

The alias is the contract. Supafone can upgrade or fail over its underlying
model while preserving the API, safety gates, telemetry, and billing behavior.
Use the explicit vendor model ID only when model pinning matters more than
managed upgrades.

`labs.enabled: true` attaches the supervisor. In managed mode, the customer's
`sl_...` Supafone key pays for the Oracle; no separate Anthropic, OpenAI, or xAI
key is required.

```json
{
  "labs": {
    "enabled": true,
    "mode": "supafone_managed",
    "model": "supafone-labs-oracle"
  }
}
```

## BYOK Oracle providers

The open SDK has first-class Oracle providers for:

| Provider | Select with | Credential | Example model |
| --- | --- | --- | --- |
| Anthropic | `llm="anthropic"` | `ANTHROPIC_API_KEY` | `claude-haiku-4-5-20251001` |
| OpenAI | `llm="openai"` | `OPENAI_API_KEY` | `gpt-4.1-mini` |
| xAI / Grok | `llm="xai"` | `XAI_API_KEY` | `grok-4-fast` |
| OpenAI-compatible | an `OpenAIProvider` instance | vendor key + `base_url` | any compatible chat-completions model |
| Offline test double | `llm="fake"` | none | deterministic local fixtures |

BYOK affects the supervisor model only. Agent runtime, telephony, STT, and TTS
remain separate choices. For example, the speaking agent can use Ultravox with
Telnyx telephony and Cartesia TTS while the Oracle uses a customer-owned OpenAI
key.

```python
from supafone_labs import SupafoneLabs
from supafone_labs.config import Settings

watcher = SupafoneLabs(
    provider="ultravox",
    llm="openai",
    oracle_model="gpt-4.1-mini",
    config=Settings(
        confidence_threshold=0.65,
        oracle_timeout_seconds=5.0,
    ),
)
```

For an OpenAI-compatible endpoint:

```python
from supafone_labs import SupafoneLabs
from supafone_labs.llm import OpenAIProvider

oracle = OpenAIProvider(
    api_key="your-provider-key",
    base_url="https://provider.example/v1",
    model="provider-model-id",
)
watcher = SupafoneLabs(provider="vapi", llm=oracle)
```

Never put provider credentials in prompts, MCP tool arguments, dashboard URLs,
or client-side bundles. Store them in environment variables or the private
Supafone credential store.

## What can be tuned

| Control | Hosted completion | Full watcher | Why it matters |
| --- | :---: | :---: | --- |
| Oracle model | Yes | Yes | Cost, latency, and reasoning depth |
| `max_tokens` / `maxTokens` | Yes | Provider/config dependent | Bounds response size and spend |
| `temperature` | Yes | Provider dependent | Controls variation for raw completions |
| Confidence threshold | — | Yes | Suppresses weak interventions |
| Oracle timeout | — | Yes | Keeps the supervisor off the latency-critical path |
| Operator guardrails | `whisper()` | Yes | Adds firm-specific policy and behavior constraints |
| Oracle instructions | — | Yes | Adjusts the supervisor's priorities |
| Belief-state prompt | — | Yes | Changes how intent, urgency, emotion, language, trust, and progress are inferred |
| Directive prompt | — | Yes | Changes how a belief becomes one bounded silent instruction |
| Scenario preset | — | Yes | Adds intake, sales, support, or other workflow guardrails |
| Apply/observe mode | — | Yes | Inject directives or score without changing the call |
| Injection adapter | — | Yes | Selects the provider-native silent control channel |
| Telemetry | — | Yes | Records model, confidence, evidence, latency, and outcome |
| Post-call analysis | — | Yes | Scores the completed call against its objective |
| Agent label | — | Yes | Connects evidence to standing-directive optimization history |

Raw hosted Oracle call:

```ts
const result = await supafone.oracle({
  model: "supafone-labs-oracle",
  maxTokens: 256,
  temperature: 0.2,
  messages: [
    { role: "system", content: "Return one short corrective directive or nothing." },
    { role: "user", content: transcript },
  ],
});
```

The higher-level `whisper()` helper accepts `model`, `maxTokens`, `temperature`,
and operator `guardrails`. The complete `SupafoneLabs` watcher additionally
maintains belief state, applies confidence/timeout gates, compiles the directive
for the selected framework, records evidence, and degrades to a no-op on error.

## Recommended production defaults

- Use `supafone-labs-oracle` for live supervision.
- Use `supafone-labs-oracle-pro` for QA and optimizer jobs where more latency is
  acceptable.
- Start with a `0.5` confidence threshold; raise it for higher-risk workflows.
- Keep a finite Oracle timeout. A late correction is worse than no correction.
- Treat `temperature` as a raw-completion control, not a substitute for evidence
  gates and operator guardrails.
- Keep the speaking and supervising models independently replaceable.

Next: [Voice Watcher Framework](self-healing-watcher.md),
[Framework Support](framework-support.md), or
[BYOK Providers](byok-providers.md).
