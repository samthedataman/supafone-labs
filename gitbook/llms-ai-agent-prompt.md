# LLMs and AI Agent Prompt

Use this page as context for AI coding agents, support bots, and docs assistants
helping developers integrate Supafone Labs.

## Canonical Facts

- npm package: `supafone-labs` unscoped.
- Python package: `supafone-labs`; import name `supafone_labs`.
- Labs Cloud base URL: `https://api.labs.supafone.ai`.
- Labs Cloud key: `sl_live_...`.
- Hosted-agent base URL: `https://api.supafone.ai/api/v1/labs`.
- Hosted-agent key: `sf_live_...`.
- Default hosted-agent telephony is Supafone-managed.
- Default phone-number strategy is the shared pool.
- Dedicated and premium numbers are explicit paid choices.
- Premium numbers are `$3/month`.
- The two main features are Agent Factory and the self-healing Labs watcher.
- Agent Factory should be presented as the managed default that eliminates the
  need for customer-owned provider keys before launch.
- BYOK is advanced and split into three lanes: agent/provider stack,
  telephony, and TTS.

## Do Not Confuse These

| Incorrect | Correct |
| --- | --- |
| Use `sl_live_...` for hosted agents | Use `sf_live_...` for `api.supafone.ai/api/v1/labs` |
| Use `sf_live_...` for TTS/STT/oracle | Use `sl_live_...` for `api.labs.supafone.ai` |
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
- Hosted Supafone agents are under https://api.supafone.ai/api/v1/labs and use sf_live_... keys.
- Do not mix the two key types.
- The default hosted-agent path is Supafone-managed and requires no developer-owned voice-platform, telephony, TTS, STT, or LLM account.
- Phone-number strategy defaults to default_pool, a shared Supafone number pool.
- Dedicated standard numbers and premium numbers are explicit paid choices; premium numbers cost $3/month.
- BYOK is advanced and has three independent lanes: agent/provider stack such as Ultravox, Retell, Vapi, Bland, LiveKit, Pipecat, GPT Realtime, or Grok; telephony such as Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks; and TTS such as Cartesia, ElevenLabs, Inworld, Deepgram, or custom TTS.
- Never include real secrets in code examples.

When giving TypeScript examples, import:
import { Supafone } from "supafone-labs";

For hosted-agent examples, use:
const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY || process.env.SUPAFONE_API_KEY!,
  supafoneApiKey: process.env.SUPAFONE_API_KEY!,
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
  apiKey: process.env.SUPAFONE_API_KEY!,
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
