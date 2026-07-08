# SDK Parity

The Python and TypeScript SDKs should let developers do the same work with the
same vocabulary. Use camelCase in TypeScript and snake_case in Python, but keep
the payload concepts identical.

## Install

```bash
pip install "supafone-labs[all]"
npm i supafone-labs
```

## One-Line Framework

Python:

```python
import supafone_labs

brain = supafone_labs.supercharge(my_agent)
```

TypeScript developers usually call the hosted cloud/client surface directly:

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY!,
});
```

## Hosted Agent Factory

TypeScript:

```ts
const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake",
  name: "Northline intake",
  assistantName: "Maya",
  websiteUrl: "https://northline.example",
  number: { search: { areaCode: "415" } },
  labs: { enabled: true, model: "gemma" },
});
```

Python:

```python
agent = supafone.labs.agents.create_inbound_with_number({
    "agentKey": "northline-intake",
    "name": "Northline intake",
    "assistantName": "Maya",
    "websiteUrl": "https://northline.example",
    "number": {"search": {"areaCode": "415"}},
    "labs": {"enabled": True, "model": "gemma"},
})
```

Python also exposes camelCase aliases for developers copying TypeScript-shaped
configs:

```python
agent = supafone.labs.agents.createInboundWithNumber({
    "agentKey": "northline-intake",
    "name": "Northline intake",
    "number": {"search": {"areaCode": "415"}},
    "labs": {"enabled": True},
})
```

## Method Map

| Capability | TypeScript | Python |
| --- | --- | --- |
| Create generic hosted agent | `supafone.labs.agents.create()` | `supafone.labs.agents.create()` |
| Create inbound agent | `createInbound()` | `create_inbound()` / `createInbound()` |
| Create outbound agent | `createOutbound()` | `create_outbound()` / `createOutbound()` |
| Create inbound + number | `createInboundWithNumber()` | `create_inbound_with_number()` / `createInboundWithNumber()` |
| Create outbound + number | `createOutboundWithNumber()` | `create_outbound_with_number()` / `createOutboundWithNumber()` |
| Search numbers | `supafone.labs.phoneNumbers.search()` | `supafone.labs.phone_numbers.search()` |
| Buy and assign number | `buyAndAssign()` | `buy_and_assign()` / `buyAndAssign()` |
| Configure telephony | `supafone.labs.telephony.configure()` | `supafone.labs.telephony.configure()` |
| Usage | `supafone.usage()` | `supafone.usage()` |
| Log snapshot | `supafone.logs()` | `supafone.logs()` |
| Log stream | `supafone.streamLogs()` | `supafone.stream_logs()` / `streamLogs()` |

## BYOK Parity

The SDKs support three distinct BYOK lanes:

| Lane | Examples |
| --- | --- |
| Agent/provider stack | Ultravox, Retell, Vapi, Bland, LiveKit, Pipecat, GPT Realtime, Grok |
| Telephony | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks |
| TTS | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS |

TypeScript:

```ts
await supafone.labs.agents.createOutbound({
  agentKey: "speed-to-lead",
  name: "Speed to lead",
  labs: {
    enabled: true,
    mode: "byok",
    managedInfrastructure: false,
    stt: { provider: "deepgram", model: "nova-3" },
    llm: { provider: "anthropic", model: "claude-3-5-sonnet" },
    tts: { provider: "cartesia", voiceId: "sonic-warm" },
  },
  byok: {
    agentProvider: {
      provider: "ultravox",
      apiKey: process.env.ULTRAVOX_API_KEY!,
    },
    telephony: {
      mode: "byok",
      provider: "telnyx",
      credentials: {
        apiKey: process.env.TELNYX_API_KEY!,
        connectionId: process.env.TELNYX_CONNECTION_ID!,
        fromNumber: "+14155550123",
      },
    },
    tts: {
      provider: "cartesia",
      apiKey: process.env.CARTESIA_API_KEY!,
    },
  },
});
```

Python:

```python
supafone.labs.agents.create_outbound({
    "agentKey": "speed-to-lead",
    "name": "Speed to lead",
    "labs": {
        "enabled": True,
        "mode": "byok",
        "managedInfrastructure": False,
        "stt": {"provider": "deepgram", "model": "nova-3"},
        "llm": {"provider": "anthropic", "model": "claude-3-5-sonnet"},
        "tts": {"provider": "cartesia", "voiceId": "sonic-warm"},
    },
    "byok": {
        "agentProvider": {
            "provider": "ultravox",
            "apiKey": os.environ["ULTRAVOX_API_KEY"],
        },
        "telephony": {
            "mode": "byok",
            "provider": "telnyx",
            "credentials": {
                "apiKey": os.environ["TELNYX_API_KEY"],
                "connectionId": os.environ["TELNYX_CONNECTION_ID"],
                "fromNumber": "+14155550123",
            },
        },
        "tts": {
            "provider": "cartesia",
            "apiKey": os.environ["CARTESIA_API_KEY"],
        },
    },
})
```

Flat `providerKeys` remains supported for simple configs and older examples,
but new docs and UI should prefer the structured `byok` object so agent
platform, telephony, and TTS credentials do not get mixed together.

## Parity Notes

- TypeScript and Python both expose hosted agent creation helpers, phone-number
  lifecycle helpers, voice catalog/preview helpers, log snapshots, and log
  streaming.
- TypeScript exports `generateCallStages(...)`; Python exports
  `generate_call_stages(...)`.
- `callStages` defaults to automatic generation from prompt and metadata unless
  explicitly disabled with `callStages: false` / `"callStages": False`.
