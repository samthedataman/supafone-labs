# supafone-labs

**The TypeScript client for the Supafone agent framework.**

Use this package to create hosted Supafone agents from code: inbound
receptionists, outbound sales agents, web agents, Supafone-managed phone
numbers, built-in stages, tools, recordings, transcripts, widgets, and Supafone
Pro watcher. It also includes the [Supafone Labs cloud](https://labs.supafone.ai)
sidecar oracle, hosted TTS/STT, live multilingual transcription, the builder,
and the adversarial QA suite.

Dependency-free. Works in Node 18+ and the browser (native `fetch` / `WebSocket`).

```bash
npm i supafone-labs
```

## Keys

The SDK talks to two related APIs:

| Environment variable | Key shape | Used for |
| --- | --- | --- |
| `SUPAFONE_LABS_API_KEY` | `sl_live_...` | Labs cloud oracle, hosted TTS/STT, logs, usage, QA, optimizer |
| `SUPAFONE_API_KEY` | `sf_live_...` | Hosted Supafone agents on `/api/v1/labs/*` |

If you only use hosted-agent methods, `SUPAFONE_API_KEY` is enough. If you use
both products from one SDK instance, pass `SUPAFONE_API_KEY` as
`supafoneApiKey`.

## Quick start

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_LABS_API_KEY! });

// The one-liner: transcript in, a silent coaching directive out.
const directive = await supafone.whisper(
  "Agent: How can I help?\nCaller: I was rear-ended — what do you charge?",
  { guardrails: "Never quote fees. Acknowledge injury first." },
);
// -> "She may be hurt — acknowledge that first, and do not state any fee."
```

Feed `directive` back into your agent however your platform injects context
(Ultravox `inject_message`, Vapi `assistant_override`, ElevenLabs
`contextual_update`, an OpenAI Realtime `session.update`, …). When it's empty,
the agent is doing fine — say nothing.

## Spawn a hosted Supafone agent

Use the same package to create finished Supafone agents from code. This hits the
Supafone API (`/api/v1/labs/*`), not a raw Ultravox endpoint: Supafone keeps the
multistage state machine, managed voice accounts, tools, recordings,
transcripts, account sync, and Supafone Pro watcher attached.

The default path is fully Supafone-managed. Developers do **not** need a Twilio
account, Ultravox account, or voice-provider account to buy a number and launch
an agent.

Supafone Labs has two main features:

- **Agent Factory**: create the complete hosted agent with managed provider
  defaults and one Supafone API key.
- **Self-healing watcher**: enable `labs.enabled` to attach the Supafone Labs
  second mind to a hosted or BYOK agent.

BYOK is advanced and split into three independent lanes:

| Lane | Examples |
| --- | --- |
| Agent/provider stack | Ultravox, Retell, Vapi, Bland, LiveKit, Pipecat, GPT Realtime, Grok |
| Telephony | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks |
| TTS | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS |

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY || process.env.SUPAFONE_API_KEY!,
  supafoneApiKey: process.env.SUPAFONE_API_KEY!,
  // Defaults to https://api.supafone.ai. Override for staging/local tests.
  // supafoneApiBaseUrl: "http://localhost:8000",
});

const capabilities = await supafone.labs.capabilities();
console.log(capabilities.default_agent_contract);

// Inbound: receptionist/intake agent + Supafone-managed phone number.
const inbound = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "medivoice-intake",
  name: "MediVoice intake",
  assistantName: "Maya",
  businessName: "MediVoice",
  websiteUrl: "https://medivoice.org",
  number: { search: { areaCode: "787" } },
  voice: {
    provider: "cartesia",
    voiceId: "Jacqueline",
  },
  labs: {
    enabled: true,
    model: "gemma",
  },
  recording: {
    enabled: true,
    recordAudio: true,
    consentRequired: true,
    announcement: "This call may be recorded for quality and training.",
    retentionDays: 30,
    redactPii: true,
  },
  transcription: {
    enabled: true,
    provider: "supafone_managed",
    language: "multi",
    diarization: true,
    timestamps: true,
  },
  tools: {
    callRouting: true,
    scheduling: true,
    sms: true,
    email: true,
    firmKnowledge: true,
    voicemail: true,
    emergencyEscalation: true,
  },
  ultravox: {
    vadSettings: {
      turnEndpointDelay: "0.384s",
      minimumTurnDuration: "0s",
      frameActivationThreshold: 0.1,
      minimumInterruptionDuration: "0.25s",
    },
    firstSpeakerSettings: {
      agent: { uninterruptible: false },
    },
  },
});

console.log(inbound.agent.agent_key);
console.log(inbound.number?.number.phone_number);
console.log(inbound.widget?.snippet);

// Outbound: sales/speed-to-lead agent + Supafone-managed caller ID.
const outbound = await supafone.labs.agents.createOutboundWithNumber({
  agentKey: "medivoice-sales",
  name: "MediVoice sales team",
  assistantName: "Maya",
  businessName: "MediVoice",
  websiteUrl: "https://medivoice.org",
  number: { search: { areaCode: "787" } },
  labs: { enabled: true, model: "gemma" },
});

console.log(outbound.number?.assignment);
```

Call artifacts are available from the same hosted-agent namespace:

```ts
await supafone.labs.calls.list({ agentKey: "medivoice-intake" });
await supafone.labs.recordings.list({ agentKey: "medivoice-intake" });
await supafone.labs.transcripts.list({ agentKey: "medivoice-intake" });
```

If you already own telephony, keep Supafone's agent framework and configure
that BYOK lane as the advanced path:

```ts
await supafone.labs.telephony.configure({
  mode: "byok",
  provider: "twilio",
  credentials: {
    accountSid: process.env.TWILIO_ACCOUNT_SID!,
    authToken: process.env.TWILIO_AUTH_TOKEN!,
    fromNumber: "+14155550123",
  },
});
```

Or configure all three BYOK lanes in one agent payload:

```ts
await supafone.labs.agents.createOutbound({
  agentKey: "speed-to-lead-byok",
  name: "Speed to lead BYOK",
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
  labs: {
    enabled: true,
    mode: "byok",
    managedInfrastructure: false,
    tts: { provider: "cartesia" },
  },
});
```

## Verify the hosted-agent path

Use the production smoke example before handing a key to a customer or testing a
new Supafone API environment:

```bash
cd supafone-labs
SUPAFONE_API_KEY=sf_live_... \
SUPAFONE_API_BASE_URL=https://api.supafone.ai \
npx tsx examples/smoke-hosted-agent.ts
```

The script discovers capabilities, presets, and voices; creates a web intake
agent; fetches it back; verifies `provider_accounts.mode` is
`supafone_managed`; verifies no developer provider keys are required; and prints
the returned widget snippet.

## Hosted voices

```ts
const wav = await supafone.tts("You're all set — talk soon!", "supafone-labs-calm-en");
// wav: Uint8Array

const text = await supafone.stt(audioBytes, { language: "en" });
```

## Live multilingual transcription

Stream PCM in, language-tagged results out (Deepgram nova-3 `multi`, code-switching):

```ts
const live = supafone.liveTranscribe({
  language: "multi",
  onResult: (r) => console.log(`[${r.languages.join(",")}]`, r.transcript, r.isFinal ? "(final)" : ""),
});
live.feed(pcmFrame); // per audio frame
live.close();
```

On Node < 22 (no global `WebSocket`), pass one in: `liveTranscribe({ WebSocketImpl: WebSocket })` from the [`ws`](https://npmjs.com/package/ws) package.

## Telemetry & reads (work with your API key)

```ts
await supafone.reportNudge({ text: "Do not quote fees", confidence: 0.9, injected: true });
await supafone.reportCall({ session_id: "call-1", score: 0.92, outcome: "clean", turns: 6 });

await supafone.balance();          // { minutes_remaining, plan, … }
await supafone.usage();            // today's usage vs caps
await supafone.logs();             // auditable whisper/billing log
await supafone.nudges();           // structured whisper feed
await supafone.metrics(7);         // injection rate, latency, by-dimension
```

## Agent builder & QA (session-scoped — call `login()` first)

The builder and `qa.run` are account features, so authenticate with a console
login before using them (everything else works with just the API key):

```ts
await supafone.login(process.env.SM_EMAIL!, process.env.SM_PASSWORD!);
console.log(supafone.isLoggedIn); // true

// A supervised builder turn: whisper + guided reply.
const turn = await supafone.builder.chat("call-1", [
  { role: "agent", text: "Hi, how can I help?" },
  { role: "caller", text: "You said I was booked but nobody called me back." },
]);
await supafone.builder.saveConfig({ agent_prompt: "…", agent_label: "intake" });

// Adversarial QA — every scenario runs A/B (supervised vs not); the delta is the lift.
const qa = await supafone.qa.run({ turns: 2 });
console.log(`+${Math.round(qa.summary.avg_lift * 100)} avg lift`);

// Improve the standing directive from graded calls (OPRO-style).
const better = await supafone.optimizer.improve("builder");
const reports = await supafone.optimizer.reports("builder");
```

All errors throw `SupafoneLabsError` (with `.status` and `.body`); catch it to
inspect gateway responses.

## Module format

Ships **both ESM and CommonJS**. `import { Supafone } from "supafone-labs"`
and `const { Supafone } = require("supafone-labs")` both work, with full types.

## API

| Method | Endpoint |
| --- | --- |
| `labs.capabilities()` | `GET /api/v1/labs/capabilities` on the Supafone API |
| `labs.agents.create/createInbound/createOutbound/list/get` | `/api/v1/labs/agents*` on the Supafone API |
| `labs.agents.createInboundWithNumber/createOutboundWithNumber` | Agent creation plus Supafone-managed number buy/assign |
| `labs.phoneNumbers.search/buy/assign/list/buyAndAssign` | `/api/v1/labs/phone-numbers*` |
| `labs.telephony.get/configure/useSupafoneManaged` | `/api/v1/labs/telephony` |
| `labs.presets.list()` · `labs.tools.list()` · `labs.voices.list()` | Supafone hosted-agent discovery |
| `whisper(transcript, opts?)` | convenience over the oracle |
| `oracle({ messages, model?, ... })` | `POST /v1/oracle/complete` |
| `tts(text, voice?)` | `POST /v1/tts` |
| `stt(audio, opts?)` | `POST /v1/stt` |
| `liveTranscribe(opts?)` | `WS /v1/stt/live` |
| `balance()` · `models()` · `voices()` · `usage()` | reads |
| `builder.chat/finish/config` | `/v1/builder/*` |
| `qa.run/history` | `/v1/qa/*` |
| `optimizer.improve/standing` | `/v1/optimizer/*` |

Get a key (5 free minutes, no card): <https://labs.supafone.ai/get-key.html>

The runtime, all provider adapters, and the offline (bring-your-own-keys) mode
are open source and MIT-licensed — the Python package `pip install supafone-labs`
is the full harness. This client is the thin cloud SDK.

MIT © Sam Savage
