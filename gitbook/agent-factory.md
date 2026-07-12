# 🏭 Agent Factory

The Agent Factory creates complete hosted agents: inbound, outbound, web, or
campaign agents with stages, voices, numbers, logs, tools, and optional
Supafone Labs watcher.

The main promise: a developer can launch with one Supafone API key. They do not
need to own Ultravox, Retell, Vapi, Twilio, Telnyx, Cartesia, ElevenLabs,
Inworld, Deepgram, OpenAI, Anthropic, or xAI accounts before the first working
agent exists.

## Default Happy Path

Start with the Supafone API key and hide provider keys until the user asks for
advanced control.

```ts
const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_API_KEY!,
});

const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake",
  name: "Northline intake",
  assistantName: "Maya",
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
```

Python:

```python
agent = supafone.labs.agents.create_inbound_with_number({
    "agentKey": "northline-intake",
    "name": "Northline intake",
    "assistantName": "Maya",
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
```

## Outbound Agents

Outbound is a first-class direction, not an inbound hack.

```ts
const outbound = await supafone.labs.agents.createOutboundWithNumber({
  agentKey: "northline-speed-to-lead",
  name: "Northline speed to lead",
  assistantName: "Maya",
  goal: "Call new leads within five minutes and book a consult.",
  number: { search: { areaCode: "415" } },
  labs: { enabled: true, mode: "supafone_managed", model: "gemma" },
});
```

## Builder UX Contract

The frontend builder should fit the core controls above the fold:

| Section | Required controls |
| --- | --- |
| Key | Supafone API key first, Labs key optional for previews/logs |
| Agent | inbound/outbound, name, assistant name, goal/system prompt |
| Stages | automatic on by default, preset selector, advanced custom stages |
| Voice | provider, voice, preview button |
| Number | default pool, dedicated, premium, BYOK |
| Labs | off/on, managed/BYOK, model |
| Export | TypeScript, Python, REST, JSON |
| Logs | snapshot and stream controls |

Advanced panels can expand for provider keys, Twilio/Telnyx credentials, custom
Ultravox runtime fields, and custom tools.

BYOK must be grouped into three separate advanced lanes:

| Lane | Builder controls |
| --- | --- |
| Agent/provider stack | Ultravox, Retell, Vapi, Bland, LiveKit, Pipecat, GPT Realtime, Grok, custom runtime |
| Telephony | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks |
| TTS | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS |

Do not make users paste provider keys to use the default Agent Factory path.
Only reveal those inputs when they choose BYOK for that lane.

## Exported Code

Export TypeScript:

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_API_KEY!,
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

supafone = Supafone(api_key=os.environ["SUPAFONE_API_KEY"])

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
