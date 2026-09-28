# BYOK Providers

BYOK means "bring your own keys." It is powerful, but it should not be the
default path. The default path is Supafone-managed infrastructure with one
Supafone key.

## Choose speaking keys for all five S2S families

`SupafoneS2S` uses the account's saved speaking-provider key when one exists;
otherwise it uses Supafone's configured platform key. Configure keys through
`client.labs.runtime`, then create or switch an agent with `SupafoneS2S`.
Vendor keys belong in account runtime configuration, not the S2S constructor
or the agent's `realtime` selection.

| Speaking family | Runtime provider ID | Your key's environment variable |
| --- | --- | --- |
| Ultravox | `ultravox` | `ULTRAVOX_API_KEY` |
| OpenAI | `openai` | `OPENAI_API_KEY` |
| Gemini | `google` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` |
| Grok | `xai` | `XAI_API_KEY` |
| Smallest AI Hydra | `smallest` | `SMALLEST_API_KEY` |

Environment names are conventions: the SDK sends the key you explicitly read.
The CLI's `--api-key-env` can read any named variable. `SUPAFONE_API_KEY`
authenticates your Supafone account separately. Keep keys in trusted server
code or your local secret store.

### Use Supafone's platform keys

Without an account override, no key setup request is needed. Create the agent
using your Supafone key. To remove an existing override and return to platform
defaults, select managed mode:

```python
import os
from supafone_labs import Supafone, SupafoneS2S

client = Supafone(api_key=os.environ["SUPAFONE_API_KEY"])
provider = "openai"  # Any runtime provider ID from the table above.
client.labs.runtime.configure(provider=provider, mode="supafone_managed")
engine = SupafoneS2S(client, provider=provider)
agent = engine.create(name="Front desk", supervisor=True)
```

```ts
import { Supafone, SupafoneS2S } from "supafone-labs";

const client = new Supafone({ apiKey: process.env.SUPAFONE_API_KEY! });
const provider = "openai";
await client.labs.runtime.configure({ provider, mode: "supafone_managed" });
const engine = new SupafoneS2S(client, { provider });
const agent = await engine.create({ name: "Front desk", supervisor: true });
```

Managed mode removes only the selected provider's encrypted account override.
It requires account-admin permission and affects **future calls for every agent
in that account using that provider**. It does not change other provider keys,
speaking selections, carrier settings or Supervisor profiles. Do not include
credentials with managed mode. Without a configured platform key, status
reports `source: "none"`; choosing managed mode does not provision a key.

### Bring your own speaking key

Use the same route for any of the five provider IDs:

```python
client.labs.runtime.configure(
    provider="openai", mode="byok",
    credentials={"api_key": os.environ["OPENAI_API_KEY"]},
)
status = client.labs.runtime.get(provider="openai")
```

```ts
await client.labs.runtime.configure({
  provider: "openai", mode: "byok",
  credentials: { apiKey: process.env.OPENAI_API_KEY! },
});
const status = await client.labs.runtime.get({ provider: "openai" });
```

Substitute the table's provider ID and matching key for Ultravox, Gemini, Grok
or Hydra. The key is encrypted on the account and takes priority over the
platform key. An unreadable override reports `source: "invalid"`; reconnect it
or explicitly return to managed mode. This setting is account-wide, not a
per-agent credential override.

### CLI

```bash
supafone runtime update --provider openai --mode byok --api-key-env OPENAI_API_KEY
supafone runtime update --provider gemini --mode byok --api-key-env GEMINI_API_KEY
supafone runtime update --provider grok --mode byok --api-key-env XAI_API_KEY
supafone runtime update --provider hydra --mode byok --api-key-env SMALLEST_API_KEY
supafone runtime update --provider ultravox --mode byok --api-key-env ULTRAVOX_API_KEY

# Inspect configuration, then explicitly restore this provider's platform key.
supafone runtime get --provider openai
supafone runtime update --provider openai --mode supafone_managed
```

`--credentials-file` remains available for a JSON object containing `api_key`
(and optionally `base_url` for Ultravox). Use it instead of `--api-key-env`.
Do not put key values in command arguments. Credentials supplied through these
inputs are scrubbed from CLI responses and error messages.

### Readiness and compatibility

`runtime.get` returns masked status. `configured` means an account override
exists; `connected` means a usable key resolves. `source` is `account`,
`platform`, `none` or `invalid`. These fields do not establish model permissions
or successful calls. Earlier Ultravox responses use `managed` and
`byok_connected`; updated responses retain these alongside the shared fields.

Omitting `mode` retains existing configure behavior. A blank key preserves an
Ultravox override; native key updates require a nonempty key. Use explicit
managed mode to remove an override.

**Release and rollout:** explicit managed reset, CLI environment-key input and
TypeScript provider readiness are part of **0.7.2** and need the corresponding
hosted backend. A configured key does not verify model access or call quality.
See [SDK installation and readiness](sdk-installation.md).

Speaking-key selection does not select Supervisor's reasoning key.
`supervisor=True` / `true` enables the default or saved coaching profile;
`supervisor={"enabled": True, "mode": "managed"}` explicitly chooses platform
reasoning. Supervisor BYOK has its own provider and key. See
[Supervisor Models: Managed and BYOK](supervisor-models.md).

## Managed compatibility defaults

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

## Independent provider domains

Do not collapse BYOK into one generic "provider keys" bucket. Hosted delivery
has three independent provisioning lanes; Supervisor deployments add independent
STT and supervisor-LLM credentials. These are five independent credential lanes:

| Lane | What it means | Common providers |
| --- | --- | --- |
| Agent/provider stack | The realtime agent, orchestration, or model runtime the customer already runs | Any of the [14 audited runtime adapters](framework-support.md) |
| Telephony | The carrier, trunk, SIP, and phone-network layer | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks |
| TTS | The voice-rendering provider | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS |
| STT | The transcript and language-authority provider | Deepgram or provider-native streams |
| Supervisor LLM | The model that forms Supervisor directives | Supafone managed, Claude, OpenAI, Gemini, OpenRouter, Groq, Cerebras |

These independent lanes do not imply fourteen hosted runtime choices. They describe the adapter and credential boundaries around a speaking runtime.

Each domain can be managed by Supafone or brought by the customer. For example,
a customer can bring Telnyx telephony and Cartesia TTS while still using
Supafone's managed supervisor, or bring an entire Ultravox stack and use Supafone
only for self-healing directives and logs.

## Managed compatibility and native S2S runtime

Hosted Agent Factory has two direct speaking-runtime lanes. The managed
Ultravox-compatible lane retains external TTS and language/voice profiles.
The native realtime lane selects among six native catalog S2S models. Both
share the custom stage planner, Manager, specialists and Supervisor, while
recording, carrier controls and live model handoff have explicit limits.
Telephony and credentials stay server-side.

### Managed Ultravox-compatible runtime

The hosted-agent **managed compatibility runtime** uses Supafone's platform
key by default (managed billing). You can instead run agents on your **own**
Ultravox account: your key, your billing. The agent is then both **placed and
monitored** on your key, and `runtime_mode` becomes `"byok"`.

Two ways to connect it:

**1. At agent create**, in the `byok` block:

```json
{
  "byok": {
    "ultravox": {
      "api_key": "uvx_...",
      "base_url": "https://api.ultravox.ai/api"
    }
  }
}
```

`base_url` is optional. A `byok.credentials` object is also accepted as the key
holder. The key is stored **encrypted on your account, never in the agent doc**.

**2. Later or standalone**, via `PUT /api/v1/labs/runtime`:

```bash
curl https://api.supafone.ai/api/v1/labs/runtime \
  -X PUT \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ultravox",
    "credentials": { "api_key": "uvx_...", "base_url": "https://api.ultravox.ai/api" }
  }'
```

With mode omitted, a blank Ultravox `api_key` keeps the stored key. Native
provider updates require a nonempty key. Use the shared examples above to
connect any speaking family or explicitly return to platform defaults. Earlier
Ultravox deployments return this compatibility status shape:

```json
{
  "account_id": "...",
  "provider": "ultravox",
  "managed": false,
  "byok_connected": true,
  "base_url": "https://api.ultravox.ai/api",
  "updated_at": "2026-07-11T00:00:00Z"
}
```

This compatibility lane is distinct from native realtime and from the supervisor provider keys below: those bring
your own STT/LLM/TTS for supervision, while this runs the agent itself on your
Ultravox account. See [Hosted Agents API](hosted-agents-api.md) for the full
create/runtime contract and the runtime block returned on agent create.

### Native realtime Agent Factory

Native realtime uses `realtime: { provider, model, voice }` with
`gpt-realtime-2.1`, `gpt-live-1`, `gemini-3.1-flash-live-preview`, `grok-voice-latest`,
`hydra-v1.0`, or `hydra-v1.1`. Use a configured platform key or optionally connect an
OpenAI, Google, xAI, or Smallest AI account key through `PUT /api/v1/labs/runtime`, then use
Supafone-managed, Twilio, Telnyx, Plivo,
or SIP phone transport. The native path shares the custom stage planner,
Manager, specialist consultations and Supervisor, with opt-in recording,
widgets and configured carrier controls. Keys and model access still need
verification. See [Shared runtime, Manager and teams](shared-agent-runtime.md).

All five Agent Factory speaking families support Supervisor coaching when
enabled and configured. The native `check_guidance` tool returns guidance;
Hydra uses model-reported context rather than transcripts. Speaking-model
credentials and Supervisor credentials are separate readiness checks.

## BYOK Supervisor Providers

Supervisor BYOK is a per-agent `supervisor` object. It is separate from the
speaking runtime, telephony, STT, and TTS lanes:

```json
{
  "supervisor": {
    "enabled": true,
    "mode": "byok",
    "provider": "openai",
    "model": "gpt-5-mini",
    "api_key": "$OPENAI_API_KEY"
  }
}
```

The current first-class providers are `anthropic`, `openai`, `gemini`,
`openrouter`, `groq`, and `cerebras`. Supafone uses each provider's fixed
official endpoint, encrypts the submitted key, and never returns it. Use
[Supervisor Models: Managed and BYOK](supervisor-models.md) for complete Python,
TypeScript, REST, and CLI examples for all six.

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
| Gemini Live | `geminiApiKey` or Google Cloud credentials |
| Inworld Realtime | `inworldApiKey` |

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
