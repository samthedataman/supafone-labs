# BYOK Providers

BYOK means "bring your own keys." It is powerful, but it should not be the
default path. The default path is Supafone-managed infrastructure with one
Supafone key.

## Managed First

```json
{
  "labs": {
    "enabled": true,
    "mode": "supafone_managed",
    "managedInfrastructure": true,
    "model": "gemma"
  },
  "telephony": {
    "mode": "supafone_managed",
    "provider": "supafone"
  }
}
```

Use this when the developer wants to launch quickly and bill usage through
Supafone.

## Three BYOK Lanes

Do not collapse BYOK into one generic "provider keys" bucket in the UI. There
are three independent choices:

| Lane | What it means | Common providers |
| --- | --- | --- |
| Agent/provider stack | The realtime agent, orchestration, or model runtime the customer already runs | Ultravox, Retell, Vapi, Bland, LiveKit, Pipecat, GPT Realtime, Grok |
| Telephony | The carrier, trunk, SIP, and phone-network layer | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks |
| TTS | The voice-rendering provider | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS |

Each lane can be managed by Supafone or brought by the customer. For example,
a customer can bring Telnyx telephony and Cartesia TTS while still using
Supafone's managed watcher, or bring an entire Ultravox stack and use Supafone
only for self-healing directives and logs.

## BYOK Watcher Providers

```json
{
  "labs": {
    "enabled": true,
    "mode": "byok",
    "managedInfrastructure": false,
    "stt": { "provider": "deepgram", "model": "nova-3" },
    "llm": { "provider": "openai", "model": "gpt-4.1-mini" },
    "tts": { "provider": "elevenlabs" }
  },
  "byok": {
    "llm": { "provider": "openai", "apiKey": "$OPENAI_API_KEY" },
    "stt": { "provider": "deepgram", "apiKey": "$DEEPGRAM_API_KEY" },
    "tts": { "provider": "elevenlabs", "apiKey": "$ELEVENLABS_API_KEY" }
  }
}
```

Supported agent/provider-stack fields include:

| Provider | Field |
| --- | --- |
| Ultravox | `ultravoxApiKey` |
| Retell | `retellApiKey` |
| Vapi | `vapiApiKey` |
| Bland | `blandApiKey` |
| LiveKit | `livekitApiKey`, `livekitApiSecret` |
| Pipecat | `pipecatApiKey` |
| OpenAI Realtime | `openaiApiKey` |
| Grok/xAI | `xaiApiKey` |

Supported TTS/STT fields include:

| Provider | Field |
| --- | --- |
| Deepgram | `deepgramApiKey` |
| Cartesia | `cartesiaApiKey` |
| ElevenLabs | `elevenlabsApiKey` |
| Inworld | `inworldApiKey` |

## BYOK Telephony

```ts
await supafone.labs.telephony.configure({
  mode: "byok",
  provider: "twilio",
  credentials: {
    accountSid: process.env.TWILIO_ACCOUNT_SID!,
    apiKey: process.env.TWILIO_API_KEY_SID!,
    apiSecret: process.env.TWILIO_API_KEY_SECRET!,
    fromNumber: "+14155550123"
  }
});
```

The telephony BYOK provider can be `twilio`, `telnyx`, `plivo`, `sip`, or any
provider label the hosted API supports for that account. The UI should show
the common carriers but the SDK should pass through custom provider labels.

Common carrier credential fields:

| Provider | Common fields |
| --- | --- |
| Twilio | `accountSid`, `authToken`, `apiKey`, `apiSecret`, `fromNumber` |
| Telnyx | `apiKey`, `connectionId`, `fromNumber` |
| Plivo | `authId`, `authToken`, `fromNumber` |
| SignalWire | `projectId`, `token`, `signalwireSpaceUrl`, `fromNumber` |
| SIP/custom | `sipTrunkUri`, `sipHost`, `username`, `password`, `headers` |

Custom SIP:

```ts
await supafone.labs.telephony.configure({
  mode: "byok",
  provider: "sip",
  customSip: {
    sipTrunkUri: process.env.SIP_TRUNK_URI!,
    username: process.env.SIP_USERNAME!,
    password: process.env.SIP_PASSWORD!,
    headers: { "X-Customer": "northline" }
  }
});
```

## UI Credential Rules

- Keep Supafone-managed selected by default.
- Store BYOK keys only through secure backend/account endpoints.
- Mask stored values on readback.
- Treat blank fields on update as "keep existing value."
- Never put provider secrets in exported code unless the user explicitly asks
  for env var placeholders.
- Export env var names, not raw secrets.

Good exported code:

```ts
byok: {
  agentProvider: {
    provider: "ultravox",
    apiKey: process.env.ULTRAVOX_API_KEY!
  },
  telephony: {
    mode: "byok",
    provider: "telnyx",
    credentials: { apiKey: process.env.TELNYX_API_KEY! }
  },
  tts: {
    provider: "cartesia",
    apiKey: process.env.CARTESIA_API_KEY!
  }
}
```

Bad exported code:

```ts
providerKeys: {
  cartesiaApiKey: "real-secret-here"
}
```

## When BYOK Is Worth It

Use BYOK when the customer:

- already has a negotiated vendor contract,
- needs vendor-specific voice/model controls,
- has existing telephony compliance infrastructure,
- wants invoices to remain with the provider,
- needs migration from an existing voice stack.

Otherwise, use Supafone-managed.
