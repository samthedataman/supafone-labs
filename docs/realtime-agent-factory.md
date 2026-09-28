# Native realtime Agent Factory

Supafone's S2S harness connects a provider-native speech-to-speech model to
one agent's prompt, supported tools, fixed stages, and browser or phone audio.
Agent Factory creates that durable agent; its `realtime` selection chooses
the speaking model. Updating the selection reuses the native agent contract
for the next session. Model voices and behavior remain provider-specific.

The native transport is separate from the managed Ultravox compatibility path.
Both support Supafone Supervisor coaching; external stacks can also connect
through standalone Supervisor adapters. Omitting `realtime` when creating an agent keeps the managed compatibility
runtime. Apply `UltravoxS2S` (or update `realtime: null`) to switch an existing
native agent back to that runtime.

Use this guide when the speaking model itself should own the live audio loop.
Use [Supafone Supervisor](https://labs.supafone.ai/docs/supafone-supervisor/) when you want to keep another
agent stack and add supervision.

Want to keep your own TTS voice? Choose [Ultravox + custom TTS](voice-output-modes.md) through the same shared interface. This native guide covers models that own their audio output; external TTS is not supported on these native paths.

## One interface, five provider families

The public `SupafoneS2S` superclass has `UltravoxS2S`, `OpenAIS2S`,
`GeminiS2S`, `GrokS2S`, and `HydraS2S` provider classes. They produce the same
Agent Factory selection shape, so an application can choose a provider and
reuse the same create, update, and preview workflow. See
[Shared S2S Interface](unified-s2s.md) for Python and TypeScript examples.

Ultravox remains the default managed runtime. The other four families provide
six native model choices below. A common interface does not erase differences
in transcripts, voices, tool behavior, or runtime features.

## Supported catalog

The catalog is the source of truth. Call `GET /api/v1/agents/catalog` or
`GET /api/v1/labs/capabilities` instead of hard-coding the list in a builder.

| Provider | `realtime.provider` | Model | Default voice | Status | Audio input/output |
| --- | --- | --- | --- | --- | --- |
| OpenAI | `openai` | `gpt-realtime-2.1` | `marin` | Available | 24 kHz / 24 kHz |
| OpenAI | `openai` | `gpt-live-1` | `marin` | Available | 24 kHz / 24 kHz |
| Google | `google` (also `gemini`/`gemini_live` in the product API) | `gemini-3.1-flash-live-preview` | `Puck` | Preview | 16 kHz / 24 kHz |
| xAI | `xai` (also `grok`/`grok_voice` in the product API) | `grok-voice-latest` | `eve` | Available | 24 kHz / 24 kHz |
| Smallest AI | `smallest` | `hydra-v1.0` | `sterling` | Available | 16 kHz / 48 kHz |
| Smallest AI | `smallest` | `hydra-v1.1` | `maya` | Available | 16 kHz / 24 kHz |

GPT Live delegates reasoning and tools to GPT-5.6 Luna. The OpenAI key used by
the workspace must be allowed to use both models. Gemini is marked preview
because the provider API is still subject to change.

Hydra currently supports English only. It uses native model voices and does not emit transcript events. Its
initial instructions and voice are fixed for a session. See
[Hydra capabilities](#hydra-capabilities) before choosing it for a workflow
that requires transcripts or live persona changes.

Every catalog entry currently advertises both authenticated browser and phone
transport for these phone providers:

- Supafone-managed phone (`native` / `supafone_managed`)
- BYO Twilio (`byo_twilio`)
- BYO Telnyx (`byo_telnyx`)
- BYO Plivo (`byo_plivo`)
- BYO SIP (`byo_sip`)

A catalog entry means an adapter exists. The selected model needs a configured
Supafone platform key or an account BYOK key. Phone delivery also needs a
reachable public application URL and managed or BYO carrier setup. Catalog
presence alone does not verify model access or a successful live call.

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

supafone = Supafone(api_key="sl_live_...")
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

## Managed credentials and optional BYOK

Use your Supafone application key to create agents. For each selected model,
the server uses the account's encrypted provider key when present; otherwise
it uses Supafone's configured platform key. Customers do not need their own
provider account when that platform key is available. Keys never belong in
the agent's `realtime` selection or browser code.

Check `GET /api/v1/labs/runtime?provider=google` (or `openai`, `xai`, `smallest`). Status
reports `configured`, `connected`, and `source`: `account` for BYOK, `platform`
for managed credentials, `none` for missing configuration, and `invalid` for
an unreadable saved key. `connected` means a credential resolves, not that a
provider has accepted a live connection. Verify model access with a preview.

To override the platform key with your own provider account, configure BYOK:

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

Use `openai`, `google`, `xai`, or `smallest` for native realtime. Google accepts either a
Gemini or Google API key. Environment fallback names are `OPENAI_API_KEY`,
`GEMINI_API_KEY`/`GOOGLE_API_KEY`, `XAI_API_KEY`, and `SMALLEST_API_KEY` when the platform is
configured to supply them. Do not put a key inside `realtime` or log it in a
client payload.

Optional BYOK configuration is also available through both SDKs:

```ts
await supafone.labs.runtime.configure({
  provider: "openai",
  credentials: { apiKey: process.env.OPENAI_API_KEY! },
});
```

```python
import os

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
await supafone.labs.telephony.configure({
  mode: "byok",
  provider: "twilio", // "telnyx", "plivo", or "sip"
  credentials: {
    // Supply the required fields for the selected carrier on your server.
  },
});
```

This configures the account's phone provider and can affect agents using that
account's carrier settings. It is not a per-agent model update. Check existing
number assignments and routing before changing a shared carrier configuration.

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
its carrier webhook checks. See [Phone Numbers](https://labs.supafone.ai/docs/phone-numbers/) and the
private product's [SIP architecture guide](https://labs.supafone.ai/docs/https://github.com/samthedataman/supafone/blob/master/docs/architecture/realtime-sip/)
for carrier-specific infrastructure.

## REST contract

| Operation | Route |
| --- | --- |
| Discover models | `GET /api/v1/agents/catalog` or `GET /api/v1/labs/capabilities` |
| Create agent | `POST /api/v1/labs/agents` |
| Update via SDK/REST | `PATCH /api/v1/labs/agents/{agent_key}` |
| Update via product dashboard | `PUT /api/v1/agents/{agent_id}` |
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

## Hydra capabilities

Smallest AI's Hydra models provide direct audio and tool calls, with no native
transcript events. Supafone therefore cannot show or grade a Hydra transcript
as though one had been received. A separate transcription system is not
implicitly enabled. See [Smallest AI's overview](https://docs.smallest.ai/models/documentation/speech-to-speech-hydra/overview).

Hydra accepts mono PCM16 at 16 kHz. Version `hydra-v1.0` returns 48 kHz audio;
`hydra-v1.1` returns 24 kHz. The browser or carrier adapter uses the selected
model's sample rates. Use a voice from that version's catalog rather than
carrying a voice ID from another provider. See the [Hydra model card](https://docs.smallest.ai/models/model-cards/speech-to-speech/hydra).

The opening instructions and voice are fixed when Hydra connects; changing
those requires a new session. Only tool definitions can be updated mid-session.
Supafone keeps stage authority on its server and communicates approved stage
instructions through tool results. This is not a live rewrite of Hydra's
persona. See [session behavior](https://docs.smallest.ai/models/documentation/speech-to-speech-hydra/managing-sessions)
and [tool calling](https://docs.smallest.ai/models/documentation/speech-to-speech-hydra/tool-calling).

Configure `SMALLEST_API_KEY` on the Supafone server for managed Hydra access,
or store an optional account key with provider `smallest`. Missing credentials
remain setup required. Adding the adapter does not configure a production key
or establish successful live calls.

## Supervisor coaching across all five speaking families

Enable `supervisor: true` (Python `"supervisor": True`) when creating an agent,
or supply the existing managed/BYOK `supervisor` configuration. Supervisor is
independent of the speaking model: Ultravox, OpenAI, Gemini, Grok, and Hydra
all support hosted coaching. The same call-scoped coach is used for native
browser sessions and Supafone-managed, Twilio, Telnyx, Plivo, and SIP calls.
Each transport still needs its own configuration and live validation.

```ts
import { Supafone, HydraS2S } from "supafone-labs";

const client = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN! });
const engine = new HydraS2S(client, { model: "hydra-v1.1", voice: "maya" });
await engine.create({
  agentKey: "coached-intake",
  name: "Coached intake",
  description: "Understand the caller's request and verify the booking result.",
  supervisor: true,
});
```

```python
from supafone_labs import Supafone, OpenAIS2S

client = Supafone(api_key="sl_live_...")
engine = OpenAIS2S(client, model="gpt-realtime-2.1", voice="marin")
engine.create({
    "agentKey": "coached-intake",
    "name": "Coached intake",
    "description": "Understand the request and verify the booking result.",
    "supervisor": True,
})
```

### Observe, reason, return guidance

| Speaking path | Observation and delivery |
| --- | --- |
| Managed Ultravox, including compatible custom TTS | Existing call observation and deferred guidance delivery |
| Native OpenAI, Gemini, Grok | Provider transcripts and server tool outcomes inform a background coach; the model receives available guidance in a `check_guidance` tool result |
| Native Hydra | No native transcripts. `check_guidance(context)` supplies **model-reported context**; the coach checks it alongside server tool outcomes and returns guidance through the same tool result |

The native model is instructed to check for guidance at appropriate turn/tool
boundaries. Supervisor never speaks to the caller, forces a new response, or
interrupts the audio stream. A slow or unavailable Supervisor yields no
instruction and the call continues. Tool-result delivery is a request by the
speaking model, not a guarantee that it checks on every turn or follows a note.

Hydra context is explicitly recorded as `model_reported_context`, not a
transcript or an independently verified quote. Provider transcript paths use
`provider_transcript`. The server's actual tool result remains authoritative
for whether a booking or another operation succeeded. Hydra's persona and
voice remain fixed during the session; a coaching tool result does not rewrite
them.

### Supported, enabled, and ready are different

Native runtime metadata separates `supervisor: true` (supported) from
`supervisor_enabled` (the saved agent setting),
`supervisor_credentials_configured` (whether the Supervisor credential resolves),
`supervisor_observation`
(`provider_transcript` or `model_reported_context`), and
`supervisor_delivery: "tool_result"`. Support or an enabled setting does not
establish working credentials or a live coach. Even configured credentials
do not verify provider access or successful inference. Configure the selected managed
or BYOK Supervisor model separately from the speaking model, and inspect call
activity before treating coaching as running.

See [Supervisor Models: Managed and BYOK](https://labs.supafone.ai/docs/supervisor-models/) for model
configuration. The [standalone adapter matrix](https://labs.supafone.ai/docs/framework-support/) describes
external sessions; Hydra's hosted coaching does not imply a standalone Hydra
Supervisor adapter exists.

## Feature boundaries

Native realtime is intentionally explicit. Current runtime responses report:

- browser preview and carrier phone transport: supported;
- fixed intake → booking → confirmation stages: supported;
- provider-native tools and account-scoped agent configuration: supported;
- Supervisor coaching: supported when enabled and configured; native delivery uses `check_guidance`;
- transcripts: provider-dependent; Hydra has no native transcript events;
- recording, human transfer, DTMF navigation, and
  specialist-team handoff, public web widgets, and live language/voice profile switching: not implemented
  on this transport;
- live carrier quality, regional reachability, and model access: require a
  deployment test with real credentials.

When recording, transfer, or a full planner is required, use the
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
