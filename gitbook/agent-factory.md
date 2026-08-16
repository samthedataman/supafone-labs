# Agent Factory

Agent Factory is the shortest path from “this business needs an AI caller” to
a working, observable agent. Describe the job in the language you would use to
train a new employee; Supafone assembles the prompts, call stages, runtime,
voice, tools, logs, and optional phone number.

The main promise: a developer can launch with one Supafone key. They do not
need to own Ultravox, Retell, Vapi, Twilio, Telnyx, Cartesia, ElevenLabs,
Inworld, Deepgram, OpenAI, Anthropic, or xAI accounts before the first working
agent exists.

### What your customer receives

- an inbound receptionist, outbound caller, web agent, or campaign agent;
- a real staged conversation instead of one fragile mega-prompt;
- editable prompts, voices, tools, escalation rules, and business knowledge;
- transcripts, recordings, call status, QA, and a signed-in dashboard;
- a managed first-run path and BYOK controls when their infrastructure is
  ready; and
- Voice Watcher supervision attached by default, so the agent can be observed
  and corrected rather than merely launched.

### What the developer no longer rebuilds

- model-key plumbing in the browser;
- prompt generation and stage validation;
- provider-specific voice and telephony payloads;
- call-state transitions and tool-truth rules;
- number assignment, webhook wiring, transcript storage, and dashboard links;
- separate SDK and MCP implementations for the same action.

The generated plan remains plain JSON. Your application can preview, edit,
approve, diff, and version it before it reaches a caller.

## Default Happy Path

Start with the Supafone API key and hide provider keys until the user asks for
advanced control.

```ts
const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_TOKEN!,
});

const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake",
  name: "Northline intake",
  assistantName: "Maya",
  description: "Answer new inquiries, understand the request, and book the right next step.",
  websiteUrl: "https://northline.example",
  number: {
    search: { areaCode: "415" },
    numberStrategy: "default_pool"
  },
  labs: {
    enabled: true,
    mode: "supafone_managed",
    model: "gemma"
  }
});

console.log(agent.call_plan?.summary);
console.log(agent.call_plan?.call_stages); // the exact stages now running
```

### Optional live language and voice routing

Live routing is an Agent Factory opt-in. It is **off by default**, so existing
agents and manually built product agents keep their current language and voice
behavior.

The smallest configuration enables English and Spanish with compatible voices
selected from the account's live voice catalog:

```ts
const agent = await supafone.labs.agents.createInbound({
  agentKey: "northline-bilingual",
  name: "Northline bilingual intake",
  languageVoiceRouting: true,
});
```

Use `routingLanguages` to configure two to four languages. The first language
controls the greeting:

```ts
const agent = await supafone.labs.agents.createInbound({
  agentKey: "northline-multilingual",
  name: "Northline multilingual intake",
  languageVoiceRouting: true,
  routingLanguages: ["es-MX", "en-US", "vi-VN"],
});
```

When the caller clearly requests or speaks another configured language, the
same call continues with that language's selected voice. The current call
stage, collected facts, campaign context, and available tools remain active.
The server never routes from accent alone.

Voice selection is automatic by default. Advanced applications can provide a
current catalog voice for each language:

```ts
const agent = await supafone.labs.agents.createInbound({
  agentKey: "northline-curated",
  name: "Northline curated multilingual intake",
  languageVoiceRouting: true,
  languageProfiles: [
    { language: "en-US", voice: { provider: "cartesia", voiceId: "<catalog-voice-id>" } },
    { language: "es-MX", voice: { provider: "cartesia", voiceId: "<catalog-voice-id>" } },
  ],
});
```

Only the preference contract is published in the SDK. Detection policy,
provider resolution, live call-state transitions, and telephony implementation
remain server-side Supafone infrastructure.

The first configured language owns the opening. If it is not English, Agent
Factory translates the supplied or generated greeting during provisioning and
returns translation status with the resolved profiles. See
[Live Language and Voice Routing](live-language-voice-routing.md) for REST,
Python, TypeScript, MCP, PSTN, campaign, WebRTC, and troubleshooting details.

Python:

```python
agent = supafone.labs.agents.create_inbound_with_number({
    "agentKey": "northline-intake",
    "name": "Northline intake",
    "assistantName": "Maya",
    "description": "Answer new inquiries, understand the request, and book the right next step.",
    "websiteUrl": "https://northline.example",
    "number": {
        "search": {"areaCode": "415"},
        "numberStrategy": "default_pool",
    },
    "labs": {
        "enabled": True,
        "mode": "supafone_managed",
        "model": "gemma",
    },
})

print(agent["call_plan"]["summary"])
```

Python uses the same opt-in:

```python
agent = supafone.labs.agents.create_inbound({
    "agentKey": "northline-bilingual",
    "name": "Northline bilingual intake",
    "languageVoiceRouting": True,
    "routingLanguages": ["en-US", "es-MX"],
})
```

## Outbound Agents

Outbound is a first-class direction, not an inbound hack.

```ts
const outbound = await supafone.labs.agents.createOutboundWithNumber({
  agentKey: "northline-speed-to-lead",
  name: "Northline speed to lead",
  assistantName: "Maya",
  goal: "Call new leads within five minutes and book a consult.",
  description: "Call warm, consented leads, understand fit and urgency, then book a consult without pressure.",
  number: { search: { areaCode: "415" } },
  labs: { enabled: true, mode: "supafone_managed", model: "gemma" },
});
```

## Builder UX Contract

The frontend builder should fit the core controls above the fold:

| Section | Required controls |
| --- | --- |
| Key | One `SUPAFONE_TOKEN` first; scoped overrides stay advanced |
| Agent | inbound/outbound, name, assistant name, goal/system prompt |
| Stages | automatic on by default, preset selector, advanced custom stages |
| Voice | provider, voice, preview button |
| Number | default pool, dedicated, premium, BYOK |
| Labs | off/on, managed/BYOK, model |
| Export | TypeScript, Python, REST, JSON |
| Logs | snapshot and stream controls |

Advanced panels can expand for provider keys, Twilio/Telnyx credentials, custom
Ultravox runtime fields, and custom tools.

BYOK must keep hosted-delivery credentials in separate advanced lanes:

| Lane | Builder controls |
| --- | --- |
| Agent/provider stack | [Fourteen audited runtime adapters](framework-support.md) plus custom runtime |
| Telephony | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks |
| TTS | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS |

Do not make users paste provider keys to use the default Agent Factory path.
Only reveal those inputs when they choose BYOK for that lane.

## Exported Code

Export TypeScript:

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_TOKEN!,
});

await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake",
  name: "Northline intake",
  assistantName: "Maya",
  websiteUrl: "https://northline.example",
  number: { search: { areaCode: "415" }, numberStrategy: "default_pool" },
  labs: { enabled: true, mode: "supafone_managed", model: "gemma" },
});
```

Export Python:

```python
from supafone_labs import Supafone

supafone = Supafone(api_key=os.environ["SUPAFONE_TOKEN"])

supafone.labs.agents.create_inbound_with_number({
    "agentKey": "northline-intake",
    "name": "Northline intake",
    "assistantName": "Maya",
    "websiteUrl": "https://northline.example",
    "number": {"search": {"areaCode": "415"}, "numberStrategy": "default_pool"},
    "labs": {"enabled": True, "mode": "supafone_managed", "model": "gemma"},
})
```

Export JSON for replay/debugging:

```json
{
  "agentKey": "northline-intake",
  "name": "Northline intake",
  "assistantName": "Maya",
  "description": "Answer new inquiries, understand the request, and book the right next step.",
  "websiteUrl": "https://northline.example",
  "number": { "search": { "areaCode": "415" }, "numberStrategy": "default_pool" },
  "labs": { "enabled": true, "mode": "supafone_managed", "model": "gemma" }
}
```

## Convenience Defaults

The Agent Factory should infer as much as possible:

- `agentKey` from `name`,
- inbound preset from an intake/receptionist/support prompt,
- outbound preset from sales, follow-up, or speed-to-lead language,
- `runtimeMode: "multi_stage"` unless explicitly disabled,
- shared number pool unless dedicated or premium is selected,
- Supafone-managed voice/telephony/provider accounts unless BYOK is selected.

## Public API, Not an SDK-Only Feature

The SDKs are typed conveniences over a normal authenticated REST contract:

```http
POST https://api.supafone.ai/api/v1/labs/agent-plans
POST https://api.supafone.ai/api/v1/labs/agents
Authorization: Bearer $SUPAFONE_TOKEN
```

The first endpoint lets a product show the complete plan for review. The second
creates the agent and installs that plan into the real stage runtime. The
Python SDK, TypeScript SDK, and MCP server call these same endpoints, so a
developer can choose the interface that fits their stack without losing
capabilities.

## Fixed Language and Voice Intent

Agent Factory can resolve a current provider voice from plain-language intent:

```ts
await supafone.labs.agents.createInbound({
  name: "Spanish intake",
  preferredLanguage: "es-MX",
  voicePreference: {
    description: "warm Latin American Spanish intake voice",
    configuredOnly: true,
  },
});
```

`preferredLanguage` applies one validated language and compatible voice for the
entire call. It does not add a language-switch tool or change voices mid-call.
See [Dynamic Voice Catalog and Selection](voice-catalog-and-selection.md).

## Advanced BYOK Agent Factory

Developers can bring any combination of their own runtime, telephony, and TTS
providers while still using the same agent creation method:

```ts
await supafone.labs.agents.createOutbound({
  agentKey: "speed-to-lead-byok",
  name: "Speed to lead BYOK",
  goal: "Call new leads quickly, qualify fit, and book the next step.",
  labs: {
    enabled: true,
    mode: "byok",
    managedInfrastructure: false,
    llm: { provider: "openai", model: "gpt-4.1-mini" },
    stt: { provider: "deepgram", model: "nova-3" },
    tts: { provider: "cartesia", voiceId: "sonic-warm" }
  },
  byok: {
    agentProvider: {
      provider: "ultravox",
      apiKey: process.env.ULTRAVOX_API_KEY
    },
    telephony: {
      mode: "byok",
      provider: "telnyx",
      credentials: {
        apiKey: process.env.TELNYX_API_KEY,
        connectionId: process.env.TELNYX_CONNECTION_ID,
        fromNumber: "+14155550123"
      }
    },
    tts: {
      provider: "cartesia",
      apiKey: process.env.CARTESIA_API_KEY
    }
  }
});
```

Custom SIP trunks are first-class pass-through config:

```ts
await supafone.labs.agents.createInbound({
  agentKey: "custom-sip-frontdesk",
  name: "Custom SIP front desk",
  telephony: {
    mode: "byok",
    provider: "sip",
    customSip: {
      sipTrunkUri: process.env.SIP_TRUNK_URI,
      username: process.env.SIP_USERNAME,
      password: process.env.SIP_PASSWORD
    }
  },
  ultravox: {
    customSip: {
      sipTrunkUri: process.env.SIP_TRUNK_URI
    }
  },
  labs: { enabled: true, mode: "supafone_managed" }
});
```
