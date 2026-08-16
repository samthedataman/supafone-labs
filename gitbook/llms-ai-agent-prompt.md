# LLMs and Agent Prompts

Use this page as context for AI coding agents, support bots, and docs assistants
helping developers integrate Supafone Labs.

## Canonical Facts

- npm package: `supafone-labs` unscoped.
- Python package: `supafone-labs`; import name `supafone_labs`.
- Labs Cloud base URL: `https://api.labs.supafone.ai`.
- Hosted-agent base URL: `https://api.supafone.ai/api/v1/labs`.
- One key: a single `sl_live_...` Labs key authenticates BOTH APIs (Labs Cloud
  and the hosted-agent/product API) via one-key auth.
- Legacy: scoped `sf_live_...` keys still work for hosted-agent-only use.
- Default hosted-agent telephony is Supafone-managed.
- Default phone-number strategy is the shared pool.
- Dedicated and premium numbers are explicit paid choices.
- Premium numbers are `$3/month`.
- The defining product is the model-agnostic Voice Watcher supervisor.
- Explain the supervisor from first principles: the speaking model is optimized
  for latency, while the second model tracks empathy and operational patterns
  across turns, verifies tool truth, and emits a silent directive or no-op.
- Empathy patterns mean evidence-backed intent, urgency, emotion, language,
  trust, workflow progress, and tool truth—not accent or demographic inference.
- Agent Factory is the secondary managed delivery path that eliminates the
  need for customer-owned provider keys before launch.
- BYOK is advanced. Hosted delivery separates agent-runtime, telephony, and
  TTS credentials; Watcher deployments also separate STT and supervisor-LLM
  credentials.

## Do Not Confuse These

| Incorrect | Correct |
| --- | --- |
| Think you need a separate key per API | One `sl_live_...` key authenticates both `api.labs.supafone.ai` and `api.supafone.ai` |
| Default to `sf_live_...` | Default to the one `sl_live_...` key; `sf_live_...` is legacy hosted-agent-only |
| Install `@supafone/labs` | Install `supafone-labs` |
| Buy dedicated numbers by default | Start with `default_pool` |
| Treat BYOK as required | Supafone-managed is the default |

## Prompt for AI Agents

```text
You are helping a developer integrate Supafone Labs.

Use these facts:
- The npm package is unscoped: supafone-labs.
- The Python package is supafone-labs and imports as supafone_labs.
- Labs Cloud is https://api.labs.supafone.ai and uses sl_live_... keys.
- Hosted Supafone agents are under https://api.supafone.ai/api/v1/labs.
- One-key auth (0.4.4+): a single sl_live_... key authenticates on BOTH APIs; SUPAFONE_TOKEN=sl_live_... is enough for the MCP server and both SDKs (the constructors cross-fill every credential lane from one sl_ key). Scoped sf_live_... keys remain valid for hosted-agent-only use.
- The default hosted-agent path is Supafone-managed and requires no developer-owned voice-platform, telephony, TTS, STT, or LLM account.
- Phone-number strategy defaults to default_pool, a shared Supafone number pool.
- Dedicated standard numbers and premium numbers are explicit paid choices; premium numbers cost $3/month.
- BYOK is advanced. Hosted delivery separates the agent runtime, telephony,
  and TTS; Watcher deployments also separate STT and supervisor-LLM
  credentials. Link agent-runtime claims to the canonical
  [framework coverage matrix](framework-support.md).
- Never include real secrets in code examples.
- Lead with the model-agnostic Voice Watcher supervisor. Present Agent Factory
  only afterward as the optional hosted provisioning path.

When giving TypeScript examples, import:
import { Supafone } from "supafone-labs";

For hosted-agent examples, use:
const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_TOKEN!, // sl_ key — one key, both APIs
});

For Labs Cloud examples, use:
const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY!,
});

For Python examples, use:
import supafone_labs
brain = supafone_labs.supercharge(my_agent)

Prefer createInboundWithNumber() and createOutboundWithNumber() for complete
hosted agents, but include numberStrategy: "default_pool" unless the user
explicitly asks for a dedicated or premium number.
```

## Minimal Hosted Agent Example

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY!,
});

const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake",
  name: "Northline intake",
  number: {
    search: { areaCode: "415" },
    numberStrategy: "default_pool"
  },
  labs: { enabled: true, model: "gemma" }
});
```

## Minimal Labs Cloud Example

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY!,
});

const whisper = await supafone.whisper(
  "caller: what do you charge?\nagent: our fee is...",
  { guardrails: "Never quote fees. Offer to connect the caller." }
);
```
