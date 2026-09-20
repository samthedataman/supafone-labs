# Native realtime Agent Factory

Supafone's Agent Factory can run a provider-native speech-to-speech (S2S)
model directly for browser previews and phone calls. This is a separate runtime
from the managed Ultravox path and from Supafone Supervisor, which observes and
coaches an existing agent off the audio path.

Use this guide when the speaking model itself should own the live audio loop.
Use [Supafone Supervisor](supafone-supervisor.md) when you want to keep another
agent stack and add supervision.

## Supported catalog

The catalog is the source of truth. Call `GET /api/v1/agents/catalog` or
`GET /api/v1/labs/capabilities` instead of hard-coding the list in a builder.

| Provider | `realtime.provider` | Model | Default voice | Status | Audio input/output |
| --- | --- | --- | --- | --- | --- |
| OpenAI | `openai` | `gpt-realtime-2.1` | `marin` | Available | 24 kHz / 24 kHz |
| OpenAI | `openai` | `gpt-live-1` | `marin` | Available | 24 kHz / 24 kHz |
| Google | `google` (also `gemini`/`gemini_live` in the product API) | `gemini-3.1-flash-live-preview` | `Puck` | Preview | 16 kHz / 24 kHz |
| xAI | `xai` (also `grok`/`grok_voice` in the product API) | `grok-voice-latest` | `eve` | Available | 24 kHz / 24 kHz |

GPT Live delegates reasoning and tools to GPT-5.6 Luna. The OpenAI key used by
the workspace must be allowed to use both models. Gemini is marked preview
because the provider API is still subject to change.

Every catalog entry currently advertises both authenticated browser and phone
transport for these phone providers:

- Supafone-managed phone (`native` / `supafone_managed`)
- BYO Twilio (`byo_twilio`)
- BYO Telnyx (`byo_telnyx`)
- BYO Plivo (`byo_plivo`)
- BYO SIP (`byo_sip`)

A catalog entry means an adapter exists. A workspace still needs the selected
model key, a reachable public application URL, and carrier credentials before a
live call can be placed.

## Create a native realtime agent

The `realtime` object contains only the provider, model, and voice. It never
contains a browser-visible credential in the returned agent document.

TypeScript:

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_API_KEY!,
});

const agent = await supafone.labs.agents.createInbound({
  agentKey: "northline-realtime",
  name: "Northline realtime intake",
  assistantName: "Maya",
  description: "Answer questions, capture the request, and book the next step.",
  realtime: {
    provider: "google",
    model: "gemini-3.1-flash-live-preview",
    voice: "Puck",
  },
  telephony: {
    mode: "supafone_managed",
    provider: "supafone",
  },
});
```

Python:

```python
from supafone_labs import Supafone

supafone = Supafone(api_key="sf_live_...")
agent = supafone.labs.agents.create_outbound({
    "agentKey": "northline-realtime-follow-up",
    "name": "Northline realtime follow-up",
    "goal": "Call a consented lead and book a consultation.",
    "realtime": {
        "provider": "xai",
        "model": "grok-voice-latest",
        "voice": "eve",
    },
    "telephony": {"mode": "byok", "provider": "telnyx"},
})
```

Native realtime agents use a fixed three-stage contract: intake, booking, and
confirmation. The hosted call planner is skipped because provider-native audio
sessions cannot safely accept arbitrary client-generated stage payloads. The
selected model, voice, and tools remain account-scoped and durable.

## Connect model credentials

Connect the selected provider before starting a live call. Credentials are
stored encrypted and status responses are masked.

```bash
curl "$SUPAFONE_API_BASE_URL/api/v1/labs/runtime" \
  -X PUT \
  -H "Authorization: Bearer $SUPAFONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "google",
    "credentials": {"api_key": "AIza..."}
  }'
```

Use `openai`, `google`, or `xai` for native realtime. Google accepts either a
Gemini or Google API key. Environment fallback names are `OPENAI_API_KEY`,
`GEMINI_API_KEY`/`GOOGLE_API_KEY`, and `XAI_API_KEY` when the platform is
configured to supply them. Do not put a key inside `realtime` or log it in a
client payload.

The same endpoint is available through both SDKs:

```ts
await supafone.labs.runtime.configure({
  provider: "openai",
  credentials: { apiKey: process.env.OPENAI_API_KEY! },
});
```

```python
supafone.labs.runtime.configure({
    "provider": "xai",
    "credentials": {"api_key": os.environ["XAI_API_KEY"]},
})
```

`GET /api/v1/labs/runtime?provider=google` returns `{configured, connected,
source}` without returning the key. A selected key must match the selected
realtime provider; cross-provider or conflicting keys are rejected.

## Browser preview

`testCall`/`test_call` starts an authenticated, rate-limited browser session.
The response contains a one-use WebSocket ticket and the provider's audio sample
rates. It is a browser preview, not a PSTN call and not a promise that carrier
routing is ready.

```ts
const preview = await supafone.labs.agents.testCall("northline-realtime");
console.log(preview.browser_session.transport); // "supafone_realtime"
console.log(preview.browser_session.websocket_url);
```

```python
preview = supafone.labs.agents.test_call("northline-realtime")
print(preview["browser_session"]["transport"])
```

The browser connects to `wss://YOUR_API_HOST/api/v1/realtime/connect` with the
short-lived ticket. The server owns the provider WebSocket and tool execution;
model credentials never cross into the browser.

## Phone calls and carrier selection

Use the default Supafone-managed telephony path when the workspace has an
approved managed number. Use BYO telephony when the customer owns the carrier
account:

```ts
await supafone.labs.agents.update("northline-realtime", {
  telephony: {
    mode: "byok",
    provider: "twilio", // "telnyx", "plivo", or "sip"
    credentials: {
      // carrier-specific fields are stored by the private product API
    },
  },
});
```

The carrier audio adapter converts media to mono PCM16 and returns model audio
at the catalog's output rate. For outbound calls, verify the caller ID, carrier
credentials, public HTTPS/WebSocket URL, destination policy, and account credit
before dialing. For inbound calls, carrier application configuration is a
separate admin step:

- Telnyx: `PUT /api/v1/realtime/phone/inbound/{agent_id}/byo_telnyx/config`,
  then point the Telnyx application at the returned webhook URL. Telnyx
  Ed25519 webhook signatures are required.
- Plivo: `PUT /api/v1/realtime/phone/inbound/{agent_id}/byo_plivo/config`,
  then configure the returned answer, hangup, and stream-status URLs. Plivo
  signature v3 verification is required.
- SIP: configure LiveKit SIP, then call
  `POST /api/v1/realtime/sip/agents/{agent_id}/inbound` with the number and
  allowed source addresses. Send signed LiveKit events to
  `/api/v1/realtime/sip/events`.

Twilio inbound and outbound use the existing managed/BYOK telephony setup and
its carrier webhook checks. See [Phone Numbers](phone-numbers.md) and the
private product's [SIP architecture guide](https://github.com/samthedataman/supafone/blob/master/docs/architecture/realtime-sip.md)
for carrier-specific infrastructure.

## REST contract

| Operation | Route |
| --- | --- |
| Discover models | `GET /api/v1/agents/catalog` or `GET /api/v1/labs/capabilities` |
| Create/update agent | `POST /api/v1/labs/agents`, `PUT /api/v1/agents/{agent_id}` |
| Connect provider key | `GET|PUT /api/v1/labs/runtime` |
| Browser preview | `POST /api/v1/labs/agents/{agent_key}/test-call` |
| Browser audio | `WS /api/v1/realtime/connect` |
| Phone audio | `WS /api/v1/realtime/phone/{carrier}/{call_record_id}/{token}` |
| SIP inbound | `POST|DELETE /api/v1/realtime/sip/agents/{agent_id}/inbound` |
| Telnyx/Plivo inbound config | `PUT /api/v1/realtime/phone/inbound/{agent_id}/{provider}/config` |

Example create payload:

```json
{
  "agent_key": "northline-realtime",
  "name": "Northline realtime intake",
  "direction": "inbound",
  "realtime": {
    "provider": "openai",
    "model": "gpt-realtime-2.1",
    "voice": "marin"
  },
  "telephony": {
    "mode": "supafone_managed",
    "provider": "supafone"
  }
}
```

## Feature boundaries

Native realtime is intentionally explicit. Current runtime responses report:

- browser preview and carrier phone transport: supported;
- fixed intake → booking → confirmation stages: supported;
- provider-native tools and account-scoped agent configuration: supported;
- recording, Supafone Supervisor coaching, human transfer, DTMF navigation, and
  public web widgets: not implemented on this transport;
- live carrier quality, regional reachability, and model access: require a
  deployment test with real credentials.

When recording, Supervisor, transfer, or a full planner is required, use the
managed Ultravox path or bring an existing compatible stack to Supafone
Supervisor instead.

## Troubleshooting checklist

1. `invalid_credentials`: reconnect the key for the selected provider and check
   the workspace's provider status.
2. `setup_required`: configure carrier credentials, caller ID, and a public
   HTTPS/WebSocket `BASE_URL`; SIP also requires LiveKit settings.
3. Browser session unavailable: confirm the agent is active and use the
   authenticated `testCall` route rather than connecting to the provider API
   from the browser.
4. Inbound carrier rejection: verify the returned webhook URL, signature keys,
   allowed number list, and that the agent still has the selected realtime
   model.
5. SIP failures: configure `LIVEKIT_URL`, `LIVEKIT_API_KEY`,
   `LIVEKIT_API_SECRET`, and `LIVEKIT_SIP_URI`, then verify the signed webhook
   reaches `/api/v1/realtime/sip/events`.

Automated tests cover catalog validation, provider adapters, browser tickets,
carrier media, Telnyx/Plivo signature checks, SIP lifecycle, duplicate webhook
handling, and PostgreSQL claim/finalization. They do not place live calls.
