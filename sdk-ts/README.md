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
(Ultravox `send_data_message`, Vapi `add-message`, ElevenLabs
`contextual_update`, an OpenAI Realtime `conversation.item.create`, …). When
it's empty, the agent is doing fine — say nothing. Which frameworks accept a
silent directive, and the exact primitive for each, is in
[Supported frameworks](#supported-frameworks) below.

## Supported frameworks

Silent injection feeds the live agent hidden guidance it acts on but never
speaks. Two mechanisms cover every supported framework:

- **Mode A — native silent event:** speech-to-speech models take a vendor event
  that adds context without triggering speech.
- **Mode B — own the LLM:** for STT→LLM→TTS pipelines, Supafone plugs in as the
  LLM and splices a `system`/`developer` message into the prompt.

**Possible — 10 frameworks**, each with a real injection door:

| Framework | Mode | Exact primitive |
| --- | :--: | --- |
| Ultravox | A | `send_data_message` (`urgency:"later"`) — **live/proven today** |
| OpenAI Realtime | A | `conversation.item.create` (role `system`, no `response.create`) |
| Grok (xAI) | A | OpenAI-Realtime-compatible item inject |
| Gemini Live | A | `clientContent` (`turnComplete:false`, role `user`) |
| ElevenLabs | A | `contextual_update` |
| Inworld | A | OpenAI-Realtime-compatible item inject |
| Vapi | A+B | `add-message` (`triggerResponseEnabled:false`) or custom-LLM splice |
| Retell | B | `system` message into the custom-LLM turn |
| Deepgram | A+B | `UpdatePrompt`, or own the `think` LLM |
| LiveKit | B | inject into `chat_ctx` in-process |

**Impossible — Bland:** its live-call API is stop/listen/transfer only, with no
mid-call inject channel and no custom-LLM. Observe and score it, but you cannot
whisper to it live — a permanent vendor limitation, not a Supafone gap.
**Cartesia** (a TTS voice) and **Pipecat** (a DIY framework you own end to end)
are not conversational agents, so there is nothing to inject into.

Injection is *possible* for all 10, but managed delivery is wired end-to-end
**only for Ultravox today**; the other nine are supported via their native
primitive with managed delivery rolling out / BYO. A live test against any vendor
needs that vendor's key — free/trial tiers exist for all except OpenAI Realtime
(paid, no free tier). Full matrix:
[gitbook/framework-support.md](../gitbook/framework-support.md). *(The npm
package-page copy updates on the next release.)*

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
  // voiceWatcher is on by default (also accepts voice_watcher; deprecated: labs).
  // Every provisioned agent runs under the Voice Watcher framework (live
  // supervision + QA + call scoring). Set false for a raw agent.
  voiceWatcher: true,
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
agent; fetches it back; verifies `runtime.telephony.mode` is `supafone_managed`
and the runtime is managed (`runtime.managed === true`, no developer Ultravox key
required); and prints the returned widget snippet.

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

### Automatic post-call analysis (`postCallAnalysis: true`)

Turn on `postCallAnalysis` and every `reportCall()` that carries a transcript
(or structured `messages`) is automatically classified against the agent's
objective before the report is filed — generating labels: achieved/missed,
per-criterion verdicts, failure reasons, and the blended objective value.

```ts
const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY!,
  postCallAnalysis: true,
});

const { analysis } = await supafone.reportCall({
  session_id: "call-1",
  agent: "intake",
  transcript: "agent: Hi, how can I help?\ncaller: I want to book...\nagent: Booked for 3pm.",
  ground_truth: { booking_requested: true, booking_verified: true },
});
// analysis.achieved            -> true
// analysis.criteria            -> { intent_satisfied: true, actions_verified: true, … }
// analysis.failure_reasons     -> []
// analysis.objective_value     -> 0.93 (LLM score blended with ground truth)
```

The enriched report is filed server-side (feeding `optimizer.improve()` and
`/v1/optimizer/objective/stats`); billed one oracle call per analyzed call.
Reports without a transcript — or any analysis failure — fall back to the
plain zero-billed report. You can also classify explicitly with
`supafone.classifyCall({ transcript, agent })`.

## Test any phone agent

The managed tester dials any voice agent you own or are authorized to test.
The target does not need to be hosted by Supafone: PSTN is the neutral boundary,
while `aiProvider` and `telephonyProvider` are recorded as metadata.

```ts
const readiness = await supafone.tester.capabilities();
if (!readiness.phone_grader.available) throw new Error("Phone grader unavailable");

const started = await supafone.tester.call({
  toNumber: "+14155550100",
  scenario: "language_switch",
  aiProvider: "grok",
  telephonyProvider: "telnyx",
  authorized: true,
});

const finished = await supafone.tester.wait(started.session_id);
console.log(finished.transcript, finished.verdict);
```

`tester.call` places a real call and spends tester credits. It rejects missing
permission and non-E.164 numbers before sending a request.

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

// One-call auto suite: scenarios generated from the agent's OWN objective,
// each played as a mock call vs the real config, judged twice — pass/fail on
// the scenario's assertion AND an SSR grade (poorly/ok/good/great/perfectly).
const suite = await supafone.qa.suite({ count: 4, turns: 2 });
console.log(suite.summary.ssr_histogram);   // { poorly: 0, ok: 1, good: 2, great: 1, perfectly: 0 }
console.log(suite.summary.avg_ssr_score);   // 0.57

// Or just generate scenarios from any prompt (key-scoped, no login needed).
const { scenarios } = await supafone.qa.generate({ agentPrompt: "You are…", count: 5 });

// Improve the standing directive from graded calls (OPRO-style).
const better = await supafone.optimizer.improve("builder");
const reports = await supafone.optimizer.reports("builder");
```

How this compares to Hamming, Coval, Roark, Cekura, and the rest of the 2026
voice-QA field — and the roadmap it drives — lives in the docs:
[Testing Voice Agents (QA)](../gitbook/voice-qa-landscape.md).

All errors throw `SupafoneLabsError` (with `.status` and `.body`); catch it to
inspect gateway responses.

## Campaigns & real calls (account-scoped)

The outbound campaign engine behind app.supafone.ai, packaged. Authenticate
with your account (not an API key) — pass `accountToken`, or
`accountEmail` + `accountPassword` and the client logs in lazily (and
re-logs-in transparently when the token expires):

```ts
const sf = new Supafone({ accountEmail: "you@company.com", accountPassword: "..." });

const { agents } = await sf.listVoiceAgents();
const { campaign } = await sf.campaigns.create({ name: "Q3 win-back", goal: "reengage", agentId: agents[0].id });
await sf.campaigns.applyPreset(campaign.id, "win_back");          // or your custom_… preset
await sf.campaigns.addRecipients(campaign.id, [
  { name: "Jane Doe", phone: "+15551234567", outreach_consent: "yes" },
]);
await sf.campaigns.launch(campaign.id);                            // real calls + emails begin

const live = await sf.campaigns.live(campaign.id);                 // in-flight calls + listen links
await sf.placeCall({ agentId: agents[0].id, toNumber: "+15551234567" }); // ring a phone right now
```

`campaigns.live()` returns a portal link (`app.supafone.ai/app/developer`) and
a listen link per in-flight call; poll `campaigns.getCall(id)` to follow the
live transcript while a call is in progress.

## Prefer natural language? Use the MCP server

The repo ships an MCP stdio server (`services/supafone-labs/mcp/supafone_mcp.py`)
exposing this same surface — plus hosted-agent provisioning — as tools for
Claude Desktop / Claude Code. Configure it with `SUPAFONE_EMAIL` +
`SUPAFONE_PASSWORD` (campaigns/calls) and/or `SUPAFONE_API_KEY` (hosted
agents), then just ask: *"create a win-back campaign, add these leads, launch
it, and show me the calls as they happen"* — Claude replies with developer-
portal links to watch the calls live. Full tool reference lives in the repo's
`gitbook/mcp-server.md`.

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
| `reportCall(report)` · `classifyCall(input)` | `/v1/events/call_report` · `/v1/calls/classify` (auto with `postCallAnalysis: true`) |
| `builder.chat/finish/config` | `/v1/builder/*` |
| `qa.run/generate/suite/history` | `/v1/qa/*` |
| `optimizer.improve/standing` | `/v1/optimizer/*` |

Get a key (5 free minutes, no card): <https://labs.supafone.ai/get-key.html>

The runtime, all provider adapters, and the offline (bring-your-own-keys) mode
are open source and MIT-licensed — the Python package `pip install supafone-labs`
is the full harness. This client is the thin cloud SDK.

MIT © Sam Savage
