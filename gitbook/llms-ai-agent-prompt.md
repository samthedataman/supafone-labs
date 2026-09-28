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
- The product has two first-class paths: native realtime Agent Factory for
  swappable speech-to-speech models, and Supafone Supervisor for existing agent
  stacks.
- Explain the supervisor from first principles: the speaking model is optimized
  for latency, while the second model tracks empathy and operational patterns
  across turns, verifies tool truth, and emits a silent directive or no-op.
- Empathy patterns mean evidence-backed intent, urgency, emotion, language,
  trust, workflow progress, and tool truth—not accent or demographic inference.
- The managed Ultravox-compatible Agent Factory path is a compatibility lane;
  the native realtime Agent Factory path is first-class and uses the selected
  configured platform key or account BYOK override, plus carrier readiness.
- BYOK is advanced. Hosted delivery separates agent-runtime, telephony, and
  TTS credentials; Supervisor deployments also separate STT and supervisor-LLM
  credentials.

## Native realtime Agent Factory facts

- Catalog models: `gpt-realtime-2.1`, `gpt-live-1`, `gemini-3.1-flash-live-preview`, `grok-voice-latest`, `hydra-v1.0`, and `hydra-v1.1`.
- Native providers: `openai`, `google`/`gemini`, `xai`/`grok`, and `smallest`.
- All five speaking families share exported `SupafoneS2S` classes: `UltravoxS2S`, `OpenAIS2S`, `GeminiS2S`, `GrokS2S`, and `HydraS2S`.
- `create` provisions an ordinary agent; `apply(agentKey)` changes its next call; `testCall`/`test_call` previews the saved agent and never applies a selection implicitly.
- Ultravox remains the default. Native choices are six models across four families; do not claim every S2S model is supported.
- Hydra defaults to `hydra-v1.1` with `maya`; v1.0 defaults to `sterling`. It has no native transcripts and cannot change persona or voice mid-session. Fixed stage transitions use validated tool-result instructions.
- `SMALLEST_API_KEY` supplies managed Hydra credentials when configured; account BYOK overrides it. Never claim credentials or live calls are verified from the catalog alone.
- The S2S harness connects one agent prompt, supported tools, fixed stages, and audio transport to its selected speaking model.
- Native model credentials resolve server-side: account BYOK overrides a configured platform key. Customers need no vendor key when managed credentials exist.
- Check runtime status per selected provider; credential presence does not establish model entitlement or live-call quality. Phone calls also need carrier readiness.
- Changing realtime applies to new sessions; it is not a mid-call model handoff.
- Phone transports: Supafone-managed, BYO Twilio, BYO Telnyx, BYO Plivo, and BYO SIP.
- Browser preview uses `labs.agents.testCall()` / `test_call()` and `transport: "supafone_realtime"`.
- All five hosted speaking families support Supervisor coaching when enabled and configured. Native delivery uses model-invoked `check_guidance` tool results; Hydra uses model-reported context, never fabricated transcripts. Distinguish supported, enabled, and credential-ready.
- Native realtime agents use fixed intake → booking → confirmation stages and do not currently expose recording, transfer, specialist-team handoff, DTMF navigation, public widgets, or live language/voice profile switching.
- The standard managed Agent Factory/Ultravox path and the native realtime path are separate choices.

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
  and TTS; Supervisor deployments also separate STT and supervisor-LLM
  credentials. Link agent-runtime claims to the canonical
  [framework coverage matrix](framework-support.md).
- Never include real secrets in code examples.
- Present native realtime Agent Factory and Supafone Supervisor as the two
  first-class paths. Describe managed Ultravox-compatible provisioning as the
  compatibility lane for its broader hosted features; native S2S agents are also hosted by Supafone.

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

For swappable S2S agents, import a provider class (for example HydraS2S), use
create(...), then apply(agentKey) before previewing a changed model. See unified-s2s.md.

Use createInboundWithNumber() and createOutboundWithNumber() for complete
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
