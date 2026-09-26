# Hosted Agent Builder

**Dashboard:** open [Supafone agents](https://app.supafone.ai/app/agents),
select your agent, and use its native realtime model controls. The older
[Labs workspace](https://labs.supafone.ai/builder.html) is the managed Ultravox
compatibility builder and links to these S2S controls.

The hosted Agent Factory builder creates agents for Supafone's S2S harness.
Choose the speaking model, its native voice, and a browser or phone transport;
Supafone retains the agent prompt, supported tools, and fixed native stages.
The managed Ultravox compatibility runtime separately provides the broader
planner, compatible TTS voices, recording, widgets, and Supervisor attachment.

There are two builder modes:

- **Programmatic builder**: TypeScript SDK or REST calls to
  `https://api.supafone.ai/api/v1/labs` with your one `sl_live_...` key (a legacy scoped `sf_live_...` key also works).
- **Labs Cloud test builder**: session-scoped `/v1/builder/*` endpoints on
  `https://api.labs.supafone.ai` for supervised test calls, grading, QA, and
  optimizer feedback.

The builder UI should start with the one `sl_` Labs key and the hosted Agent
Factory path. BYOK provider credentials should live behind an advanced drawer.
After a working agent is created, the builder should export the exact same
configuration as TypeScript, Python, REST, MCP, and JSON.

The builder should preserve the product hierarchy:

| Role | Builder meaning |
| --- | --- |
| Native realtime Agent Factory | Swap among the four S2S models while keeping the same carrier and tool contract. |
| Supafone Supervisor | Supervise and improve an existing or managed live agent. |
| Managed compatibility Agent Factory | Create a complete hosted agent with managed defaults and no required vendor keys. |

When users open BYOK, split hosted-delivery settings into three drawers:

| BYOK drawer | Examples |
| --- | --- |
| Agent/provider stack | [Fourteen audited runtime adapters](framework-support.md) |
| Telephony | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks |
| TTS | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS |

Recording and transcription should be explicit controls: audio recording,
transcription, PII redaction, retention days, and consent announcement.

## Native realtime builder path

The builder can select OpenAI GPT Realtime 2.1, GPT Live 1, Gemini Live 3.1, or
Grok Voice. Use the selected model's configured Supafone platform key by default;
an account BYOK key overrides it. Show credential source and model/carrier
readiness before launch, and surface missing setup without requiring BYOK
when a platform key exists.

Native agents use the authenticated `supafone_realtime` browser transport and
fixed intake → booking → confirmation stages. Model switching applies to new
sessions. Recording, Supervisor coaching, transfer, DTMF, public widgets, and
live language/voice profile switching are not available on this transport.

See [Native Realtime Agent Factory](realtime-agent-factory.md) for the complete request and readiness contract.

## Programmatic managed compatibility builder

These examples omit `realtime` and use the existing Ultravox runtime. For
native S2S creation and switching, follow the [quickstart](quickstart.md).

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_TOKEN!,
});

const inbound = await supafone.labs.agents.createInbound({
  agentKey: "northline-intake",
  name: "Northline intake",
  assistantName: "Maya",
  businessName: "Northline",
  description: "Answer new inquiries, capture the facts that matter, and book or route the next step.",
  websiteUrl: "https://northline.example",
  presetKey: "general_intake_receptionist",
  runtimeMode: "multi_stage",
  labs: { enabled: true, model: "gemma" },
  tools: {
    callRouting: true,
    scheduling: true,
    sms: true,
    email: true,
    firmKnowledge: true,
    voicemail: true
  }
});

console.log(inbound.call_plan?.call_stages); // reviewed JSON now running
```

### Review before creation

Products that need an approval step can preview first, show the plan in their
own UI, let an operator edit it, and create from the approved JSON:

```ts
const plan = await supafone.generateCallStages({
  direction: "inbound",
  businessName: "Northline",
  description: "Answer new inquiries, capture the facts that matter, and book or route the next step.",
  stageCount: 5,
  stageDetail: "detailed",
});

await supafone.labs.agents.createInbound({
  agentKey: "northline-intake",
  name: "Northline intake",
  callStages: plan.call_stages,
});
```

The equivalent REST endpoint is `POST /api/v1/labs/agent-plans`; Python uses
`generate_call_stages()`; MCP uses `generate_call_stages`. All four interfaces
share one plan contract and one Supafone credential.

To add a number, use `createInboundWithNumber()` or
`createOutboundWithNumber()`. Choose the shared pool unless the user explicitly
selects a paid reserved number.

```ts
const withNumber = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-phone",
  name: "Northline phone intake",
  number: {
    search: { areaCode: "415" },
    numberStrategy: "default_pool"
  },
  labs: { enabled: true, model: "gemma" }
});
```

## Discovery Before Creation

```ts
const capabilities = await supafone.labs.capabilities();
const presets = await supafone.labs.presets.list();
const tools = await supafone.labs.tools.list();
const voices = await supafone.labs.voices.list({ provider: "cartesia" });
```

Use discovery to render UI options rather than hard-coding provider inventory.

## Labs Cloud Test Builder

The Labs Cloud builder runs supervised test turns and saves configuration under
the logged-in account. Call `login()` first.

```ts
const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY!,
});

await supafone.login(process.env.SM_EMAIL!, process.env.SM_PASSWORD!);

await supafone.builder.saveConfig({
  agent_prompt: "You are a warm intake agent. Never quote fees.",
  agent_label: "intake",
  framework: "ultravox",
  llm: { provider: "hosted" }
});

const turn = await supafone.builder.chat("call-1", [
  { role: "agent", text: "Hi, how can I help?" },
  { role: "caller", text: "What do you charge? Give me a number." }
]);

console.log(turn.whisper);
console.log(turn.agent_reply);
```

Finish a test call to grade it and feed the optimizer:

```ts
await supafone.builder.finish("call-1", [
  { role: "agent", text: "Hi, how can I help?" },
  { role: "caller", text: "What do you charge?" },
  { role: "whisper", text: "Do not quote fees; offer to connect them." },
  { role: "agent", text: "I cannot quote fees, but I can connect you with the team." }
]);
```

## Builder Copilot Wizard

`POST /v1/builder/wizard` on Labs Cloud powers the conversational copilot in
the [labs.supafone.ai builder](https://labs.supafone.ai/builder.html): one
copilot turn takes developer prose in and returns validated field updates out.
The caller sends a `fields` catalog (key, label, type, options) plus the
current `draft`; the response is `{updates, reply}` with every value clamped
to the caller's catalog — a deterministic contract the UI can apply directly
to the real form. It authenticates with an `sl_` key and bills one Supervisor
inference per turn (only when the model actually ran).

```http
POST https://api.labs.supafone.ai/v1/builder/wizard
Authorization: Bearer sl_live_...

{
  "message": "Outbound roofing quotes, warm tone, 415 number",
  "draft": {"direction": ""},
  "fields": [
    {"key": "direction", "label": "Direction", "type": "choice", "options": ["inbound", "outbound"]},
    {"key": "agent_prompt", "label": "Prompt", "type": "text"}
  ]
}
```

## Builder Contract

The builder stores:

- agent prompt and agent label,
- framework label and optional framework key,
- optional BYO agent/provider-stack settings,
- optional BYO telephony settings,
- optional BYO TTS settings,
- recording, transcription, retention, and artifact settings,
- LLM provider selection,
- masked secret fields on readback.

Blank secret fields in update payloads mean "keep the previously saved value".

## Related Docs

- [Agent Factory](agent-factory.md)
- [Call Stages](call-stages.md)
- [BYOK Providers](byok-providers.md)
- [Voices and Previews](voices-and-previews.md)
- [Call Recording and Artifacts](call-recording-artifacts.md)
- [Log Streaming](log-streaming.md)
