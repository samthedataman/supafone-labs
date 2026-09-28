# Agent Factory

Agent Factory creates a durable Supafone voice agent from a job description.
Its S2S harness connects the selected speaking model to the agent's prompt,
supported tools, stages, and browser or phone transport. You can change the
model without rebuilding the surrounding native agent integration.

## Shared S2S interface

Use the same `SupafoneS2S` interface for **Ultravox, OpenAI, Gemini, Grok,
and Smallest AI Hydra**. Provider subclasses supply the selection while Agent
Factory keeps the agent and phone identity. Ultravox stays the default; the
native catalog offers six model choices. See [the common interface](unified-s2s.md)
for the class contract and switching examples.

Model changes apply to new calls, not a live-call handoff. Capabilities remain
provider-specific: Hydra has no native transcripts and cannot change its
persona or voice mid-session. Check credentials and test the selected provider
before a customer call.

## Two voice-output choices in one Agent Factory

**Ultravox + custom TTS** keeps the existing managed phone agent and lets a
compatible Cartesia, ElevenLabs, Inworld, or Ultravox catalog voice supply its
speech. **Native S2S** selects OpenAI, Gemini, Grok, or Hydra and uses that
model's own voice list. Both are available through `SupafoneS2S`; external TTS
is not a universal voice override for native models.

[Compare both paths and create an Ultravox agent with custom TTS](voice-output-modes.md).

## Choose an S2S option

| Provider | Model | Default voice |
| --- | --- | --- |
| OpenAI | `gpt-realtime-2.1` | `marin` |
| OpenAI | `gpt-live-1` | `marin` |
| Google | `gemini-3.1-flash-live-preview` | `Puck` |
| xAI | `grok-voice-latest` | `eve` |
| Smallest AI | `hydra-v1.0` | `sterling` |
| Smallest AI | `hydra-v1.1` | `maya` |

All six native catalog models support browser previews and the same five phone
families: Supafone-managed, Twilio, Telnyx, Plivo, and SIP. Model availability
and carrier readiness depend on the deployment's configuration.

## Create a native agent

In the [Supafone dashboard](https://app.supafone.ai/app/agents), create or open
an agent, choose its speaking provider/model/voice, inspect credential status,
save, and preview it. The SDK follows the same Agent Factory contract:

```ts
import { Supafone, HydraS2S } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN! });
const engine = new HydraS2S(supafone, { model: "hydra-v1.1", voice: "maya" });
const agent = await engine.create({
  agentKey: "northline-intake",
  name: "Northline intake",
  description: "Understand the request and book the right next step.",
  supervisor: true,
  telephony: { mode: "supafone_managed", provider: "supafone" },
});
const preview = await engine.testCall("northline-intake");
```

Start with one Supafone API key. The selected model uses a configured platform
key by default; an encrypted account BYOK key overrides it. Check the model's
runtime status and test a preview before dialing. Keep provider keys on the
server. Managed phone and BYO carriers have separate readiness checks.

## Keep the coach when you switch

Set `supervisor: true` or the managed/BYOK Supervisor object on the agent.
All five speaking families support coaching, independently from the voice
choice. Native models receive guidance through `check_guidance`; Hydra passes
model-reported context because it has no transcript stream. A supported coach
must also be enabled and have its Supervisor credentials configured.
See [the hosted coaching contract](realtime-agent-factory.md#supervisor-coaching-across-all-five-speaking-families).

## Keep the workflow when you switch

```ts
import { OpenAIS2S } from "supafone-labs";

const next = new OpenAIS2S(supafone, { model: "gpt-realtime-2.1", voice: "marin" });
await next.apply("northline-intake");
const preview = await next.testCall("northline-intake");
```

Apply the selection before previewing: `testCall` uses the saved agent.
The next session uses the new model. The agent identity, instructions,
supported tools, fixed intake → booking → confirmation stages, and phone
configuration remain together. Use a voice supported by the selected model.
The native harness does not support arbitrary planner stages, recording, human transfer, specialist-team handoff, DTMF, public widgets, or live
language/voice profile switching today.

The [native S2S guide](realtime-agent-factory.md) contains Python examples,
credential status, browser audio, and carrier setup. The
[developer workflow](developer-workflows.md) covers creation and switching.

## Ultravox + custom TTS: the managed runtime

Omitting `realtime` retains the managed Ultravox compatibility runtime. The
rest of this page describes that runtime's generated planner, compatible TTS
voices, Supervisor attachment, widgets, and language-routing features. These
are distinct from the native S2S feature set above.

## Managed compatibility workflow

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

### Managed compatibility language and voice routing

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
| TTS | Hosted Ultravox: compatible Cartesia, ElevenLabs, Inworld, and catalog voices. Deepgram previews and custom SDK TTS are separate capabilities; see [voice-output choices](voice-output-modes.md). |

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

```bash
curl "https://api.supafone.ai/api/v1/labs/agents" \
  -H "Authorization: Bearer $SUPAFONE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Spanish intake","preferredLanguage":"es-MX","voicePreference":{"description":"warm Latin American Spanish intake voice","configuredOnly":true}}'
```

Use REST for these preference fields in SDK 0.6.3. For SDK creation, supply an
explicit compatible `voice` selection as shown in the
[custom TTS guide](voice-output-modes.md).

`preferredLanguage` applies one validated language and compatible voice for the
entire call. It does not add a language-switch tool or change voices mid-call.
See [Dynamic Voice Catalog and Selection](voice-catalog-and-selection.md).

## Advanced BYOK Agent Factory

Configure runtime, telephony, and TTS credentials in separate lanes. A provider
key does not add a hosted runtime bridge: use only combinations supported by
the selected runtime. The example below uses the Ultravox path with Cartesia TTS:

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
