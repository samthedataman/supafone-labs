<div align="center">

# Supafone Labs

**The voice-agent framework behind Supafone.** Create complete inbound and
outbound agents with managed numbers, voices, stages, tools, artifacts, and
Supafone Pro watcher built in — or attach the same second mind to any platform.

[![CI](https://github.com/samthedataman/supafone-labs/actions/workflows/ci.yml/badge.svg)](https://github.com/samthedataman/supafone-labs/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/supafone-labs)](https://pypi.org/project/supafone-labs/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://pypi.org/project/supafone-labs/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![API](https://img.shields.io/badge/cloud%20API-live-3fd0c9)](https://api.labs.supafone.ai/healthz)

[**Website**](https://labs.supafone.ai) ·
[**Docs**](https://labs.supafone.ai/docs.html) ·
[**Console**](https://labs.supafone.ai/console.html) ·
[**Get a free API key**](https://labs.supafone.ai/get-key.html) ·
[**API reference**](https://api.labs.supafone.ai/docs)

</div>

---

```python
import supafone_labs

brain = supafone_labs.supercharge(my_agent)   # that's the whole integration
```

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_API_KEY! });

const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake",
  name: "Northline intake",
  assistantName: "Maya",
  websiteUrl: "https://northline.example",
  number: { search: { areaCode: "415" } },
  labs: { enabled: true, model: "gemma" },
});
```

The TypeScript package is also the canonical client for the Supafone hosted
agent API at `https://api.supafone.ai/api/v1/labs`. The default path buys and
routes Supafone-managed numbers, so developers do not need to create Twilio,
Ultravox, Cartesia, Inworld, ElevenLabs, or Deepgram accounts just to ship an
agent. BYOK remains available when a team already owns those provider accounts.

## The two product pillars

Supafone Labs has two equally important features:

1. **Agent Factory**: create complete inbound, outbound, web, and campaign
   agents from one Supafone API key. This is the managed path. It eliminates
   the need to bring your own voice-platform, telephony, TTS, STT, or LLM keys
   before you can launch.
2. **Self-healing Labs watcher**: attach the Supafone second mind to a hosted
   agent or to an agent you already run. It listens beside the call, watches
   transcripts, tools, state, and outcomes, then sends silent corrective
   directives through the provider's native control channel.

Managed is the default. BYOK is available when the customer already owns
provider accounts or needs provider-specific controls. Keep the BYOK lanes
separate:

| BYOK lane | What it covers | Examples |
| --- | --- | --- |
| Agent/provider stack | The realtime agent or model runtime | Ultravox, Retell, Vapi, Bland, LiveKit, Pipecat, GPT Realtime, Grok |
| Telephony | Carrier, trunk, and phone-network credentials | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks |
| TTS | Voice rendering and voice-clone/provider credentials | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS |

Those lanes can be mixed. A team can use Supafone-managed telephony with BYOK
TTS, or BYOK Twilio/Telnyx with the managed Labs watcher, or bring the full
stack and only use Supafone for self-healing supervision and logs.

## Why this exists

**A voice agent is one mind on a stopwatch.** To sound human it must answer in
well under a second — which means the model that *talks* can never afford to
*think*. And everything that decides whether a call succeeds is thinking:
reading distress in a caller's voice, noticing they just switched to Spanish,
catching the agent about to promise something the API failed to do, remembering
that this firm never quotes fees on the phone. The latency budget forbids all
of it. That's not a prompt-engineering problem; it's an architecture problem.

**Humans solved this decades ago.** Every great call floor has a supervisor
with a headset — listening to the call, saying nothing to the customer, sliding
a note across the desk: *"she's scared, slow down"*, *"stop — don't quote the
fee"*, *"the booking didn't go through, don't say it did."* The agent keeps
talking; the note changes the call. Nobody expects the person speaking to also
be the person supervising. Yet that's exactly what we ask of every voice agent
shipped today.

**Supafone Labs is the supervisor.** A second, slower mind that runs *beside* the
call instead of inside its latency budget: it taps every turn, maintains a
live belief state — who's calling, what they want, how they feel, what language
they're speaking — and slides its note across the desk through your platform's
native silent channel. The caller never hears it. The agent reads it mid-call.

**Why silent injection, not a better prompt?** Because prompts are frozen at
call-start and calls are alive. The moment that matters — the caller starts
crying, the summary contradicts the tool result, the language flips — is by
definition the moment your prompt didn't anticipate.

**Why every platform?** Because teams switch voice stacks constantly, and the
coaching layer is exactly the part you can't afford to rewrite. One canonical
contract in, one whisper out, compiled to whatever you run this quarter.

**Why open source with a cloud?** Because a system that whispers into your
calls must be inspectable — every directive is in the audit log, and the whole
brain is MIT. The cloud exists for one reason: one key that runs the models,
the voices, and the transcription is more convenient than five vendor accounts.

**And when the second mind fails?** Nothing happens. It runs behind a timeout,
off the hot path; a stalled oracle yields no note and the call proceeds exactly
as it would have without us. Degrade-safety is tested, not promised.

## Every platform, one whisper

<div align="center">
<table>
<tr>
<td align="center" width="110"><img src="https://www.google.com/s2/favicons?domain=vapi.ai&sz=128" width="36" alt="Vapi"><br><sub><b>Vapi</b></sub></td>
<td align="center" width="110"><img src="https://www.google.com/s2/favicons?domain=retellai.com&sz=128" width="36" alt="Retell"><br><sub><b>Retell AI</b></sub></td>
<td align="center" width="110"><img src="https://www.google.com/s2/favicons?domain=elevenlabs.io&sz=128" width="36" alt="ElevenLabs"><br><sub><b>ElevenLabs</b></sub></td>
<td align="center" width="110"><img src="https://www.google.com/s2/favicons?domain=ultravox.ai&sz=128" width="36" alt="Ultravox"><br><sub><b>Ultravox</b></sub></td>
<td align="center" width="110"><img src="https://www.google.com/s2/favicons?domain=openai.com&sz=128" width="36" alt="OpenAI"><br><sub><b>GPT-Realtime</b></sub></td>
<td align="center" width="110"><img src="https://www.google.com/s2/favicons?domain=x.ai&sz=128" width="36" alt="xAI"><br><sub><b>Grok Voice</b></sub></td>
<td align="center" width="110"><img src="https://www.google.com/s2/favicons?domain=deepgram.com&sz=128" width="36" alt="Deepgram"><br><sub><b>Deepgram</b></sub></td>
</tr>
<tr>
<td align="center"><img src="https://www.google.com/s2/favicons?domain=bland.ai&sz=128" width="36" alt="Bland"><br><sub><b>Bland</b></sub></td>
<td align="center"><img src="https://www.google.com/s2/favicons?domain=pipecat.ai&sz=128" width="36" alt="Pipecat"><br><sub><b>Pipecat</b></sub></td>
<td align="center"><img src="https://www.google.com/s2/favicons?domain=livekit.io&sz=128" width="36" alt="LiveKit"><br><sub><b>LiveKit</b></sub></td>
<td align="center"><img src="https://www.google.com/s2/favicons?domain=cartesia.ai&sz=128" width="36" alt="Cartesia"><br><sub><b>Cartesia</b></sub></td>
<td align="center"><img src="https://www.google.com/s2/favicons?domain=inworld.ai&sz=128" width="36" alt="Inworld"><br><sub><b>Inworld</b></sub></td>
<td align="center"><img src="https://www.google.com/s2/favicons?domain=anthropic.com&sz=128" width="36" alt="Anthropic"><br><sub><b>Claude</b></sub></td>
<td align="center"><img src="https://www.google.com/s2/favicons?domain=twilio.com&sz=128" width="36" alt="Twilio"><br><sub><b>Twilio</b></sub></td>
</tr>
<tr>
<td align="center"><img src="https://www.google.com/s2/favicons?domain=telnyx.com&sz=128" width="36" alt="Telnyx"><br><sub><b>Telnyx</b></sub></td>
<td align="center"><img src="https://www.google.com/s2/favicons?domain=signalwire.com&sz=128" width="36" alt="SignalWire"><br><sub><b>SignalWire</b></sub></td>
<td align="center"><img src="https://www.google.com/s2/favicons?domain=vonage.com&sz=128" width="36" alt="Vonage"><br><sub><b>Vonage</b></sub></td>
<td align="center"><img src="https://www.google.com/s2/favicons?domain=plivo.com&sz=128" width="36" alt="Plivo"><br><sub><b>Plivo</b></sub></td>
<td align="center"><img src="https://www.google.com/s2/favicons?domain=jambonz.org&sz=128" width="36" alt="Jambonz"><br><sub><b>Jambonz</b></sub></td>
<td align="center"><img src="https://www.google.com/s2/favicons?domain=freeswitch.com&sz=128" width="36" alt="FreeSWITCH"><br><sub><b>FreeSWITCH</b></sub></td>
<td align="center"><img src="https://www.google.com/s2/favicons?domain=asterisk.org&sz=128" width="36" alt="Asterisk"><br><sub><b>Asterisk</b></sub></td>
</tr>
</table>
</div>

## Get started in 60 seconds

**1 — Get a key** (5 free minutes, no card):

```bash
curl -X POST https://api.labs.supafone.ai/v1/signup \
  -H "Content-Type: application/json" -d '{"email": "you@company.com"}'
# -> { "key": "sl_live_…", "free_minutes": 5.0 }   (also emailed to you)

export SUPAFONE_LABS_API_KEY=sl_live_…
```

**2 — Install and supercharge:**

```bash
pip install supafone-labs[all]
```

```python
import supafone_labs

brain = supafone_labs.supercharge(my_agent, scenario="legal_intake")
result = await brain.observe(raw_event)     # feed your platform's events
# result.actions -> the compiled native whisper (or [] if the oracle is quiet)
```

Want every finished call automatically labeled? Construct the brain with
`post_call_analysis=True` and each session end is classified against your
objective — achieved/missed, per-criterion verdicts, failure reasons — with
the enriched report filed for the optimizer:

```python
from supafone_labs import SupafoneLabs

brain = SupafoneLabs(agent=my_agent, post_call_analysis=True)
# ...calls happen...
brain.analysis("session-123")   # -> {"achieved": True, "criteria": {...}, "failure_reasons": []}
brain.last_analysis             # labels for the most recently classified call
```

With the key set, the oracle, TTS, and live multilingual STT all run on
Supafone Labs' hosted infrastructure. Without it, everything runs on **your own
vendor keys** — or fully offline on deterministic fakes. Same code, all three
modes.

**3 — Watch it work** in the [console](https://labs.supafone.ai/console.html):
your balance, usage, and an auditable log of every instruction your second
mind whispered.

## Hosted Supafone agents

Use `supafone-labs` when you want Supafone to host the whole agent:

```ts
const inbound = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake",
  name: "Northline intake",
  assistantName: "Maya",
  websiteUrl: "https://northline.example",
  number: { search: { areaCode: "415" } },
  tools: { callRouting: true, scheduling: true, sms: true, voicemail: true },
  labs: { enabled: true, model: "gemma" },
});

const outbound = await supafone.labs.agents.createOutboundWithNumber({
  agentKey: "northline-sales",
  name: "Northline sales team",
  number: { search: { areaCode: "415" } },
  labs: { enabled: true, model: "gemma" },
});
```

What Supafone handles in the default path:

- Supafone-managed phone number search, purchase, assignment, and routing.
- Managed voice provider accounts for Cartesia, Inworld, ElevenLabs-compatible,
  Ultravox, and Deepgram-backed paths.
- Multistage inbound and outbound presets instead of one flat prompt.
- Built-in tools for routing, scheduling, SMS, email, voicemail, knowledge,
  escalation, transcripts, recordings, and summaries.
- Supafone Pro live watcher/call coach.

BYOK is advanced, not required:

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

## The MCP server — run Supafone in natural language

`mcp/supafone_mcp.py` is a dependency-light MCP (Model Context Protocol) stdio
server. Point Claude Desktop, Claude Code, or any MCP client at it and the
whole platform becomes conversational — no code required:

> "Create a win-back campaign with my Northline agent, add these five leads,
> launch it, and show me the calls as they happen."

Claude builds the campaign, launches real calls, and replies with links to the
developer portal (`app.supafone.ai/app/developer`) where you watch the calls
live — in-flight calls surface with a growing transcript as the conversation
happens.

### Hook it up (Claude Desktop / Claude Code)

```json
{
  "mcpServers": {
    "supafone": {
      "command": "python3",
      "args": ["<repo>/services/supafone-labs/mcp/supafone_mcp.py"],
      "env": {
        "SUPAFONE_EMAIL": "you@company.com",
        "SUPAFONE_PASSWORD": "...",
        "SUPAFONE_API_KEY": "sf_live_...",
        "SUPAFONE_LABS_API_KEY": "sl_live_..."
      }
    }
  }
}
```

Two independent auth lanes — set the ones you use:

| Lane | Env | Unlocks |
| --- | --- | --- |
| Account login (same as app.supafone.ai) | `SUPAFONE_EMAIL` + `SUPAFONE_PASSWORD`, or `SUPAFONE_TOKEN` (a JWT) | Campaigns, real calls, live monitoring, sign links |
| API keys | `SUPAFONE_API_KEY` / `SUPAFONE_LABS_API_KEY` | Hosted-agent provisioning, numbers, Labs logs/usage/voices |

The server logs in lazily with the email/password and transparently re-logs-in
when the token expires — a long Claude session never goes stale.

### What Claude can do with it

- **Campaigns end to end** — `create_campaign`, `apply_campaign_preset`
  (built-in playbooks or your saved custom presets), `add_campaign_recipients`
  (consented leads), `launch_campaign` / `pause_campaign`, `update_campaign`
  (scripts, cadence, settings — including the e-sign document config).
- **Real phone calls** — `call_from_owned_agent` dials any number from your calling
  provider and bridges your voice agent onto the line. `list_voice_agents`
  picks the agent.
- **Live monitoring** — `monitor_campaign` returns the live funnel, the calls
  in flight *right now*, and a listen link per call plus the campaign's
  developer-portal link; `get_call` polled during a call follows the live
  transcript turn by turn.
- **E-sign** — `create_sign_link` mints a recipient's tracked tap-to-sign page
  (inherits the campaign's uploaded PDF + placed signature fields).
- **Hosted agents & numbers** — create inbound/outbound agents (with number
  provisioning), search/assign/release numbers, tail Labs logs, preview voices.

Full tool reference: [`gitbook/mcp-server.md`](gitbook/mcp-server.md). The same
campaign surface is available in code via `supafone_labs` (PyPI) and
`supafone-labs` (npm) — `client.campaigns.*` + `callFromAgent()`.

## How it works

```
                      ┌─────────────────────────────────────────────┐
  your live call ────▶│  TAP        13 platform adapters +          │
  (any platform)      │             Deepgram nova-3 multilingual    │
                      │             STT for audio-only stacks       │
                      ├─────────────────────────────────────────────┤
                      │  THINK      belief state + coaching oracle  │
                      │             (off the latency path, timeout- │
                      │             bounded, degrade-safe)          │
                      ├─────────────────────────────────────────────┤
  silent whisper ◀────│  WHISPER    compiled to the platform's      │
  (native channel)    │             native control — never spoken   │
                      └─────────────────────────────────────────────┘
```

## The Cloud API

One key fronts the whole stack — hosted oracle models, four TTS engines under
one voice namespace, and live multilingual transcription. Billed by the
minute; every request itemized.

| Endpoint | What it does |
|---|---|
| `POST /v1/signup` | Self-serve key — 5 free minutes, no card |
| `POST /v1/oracle/complete` | Hosted LLM completion (Claude / GPT / Grok, prefix-routed) |
| `GET  /v1/models` | Live model catalog, fetched hourly from vendors — **never stale** |
| `POST /v1/tts` | Managed Cartesia TTS by default; other engines are explicit BYOK choices |
| `GET  /v1/voices` | The hosted voice catalog |
| `POST /v1/stt` | Prerecorded transcription (nova-3, 10-language code-switching) |
| `WS   /v1/stt/live` | Live streaming STT — the multilingual tap, zero Deepgram account |
| `GET  /v1/usage` | Today's request counts |
| `GET  /v1/billing/balance` | Minutes remaining + top-up links |
| `GET  /v1/logs` | The audit trail: every whisper, timestamped and billed |
| `POST /v1/qa/generate` | Adversarial test scenarios generated from your agent's own prompt |
| `POST /v1/qa/suite` | One-call auto QA suite: mock calls vs your real config, pass/fail + SSR grades |
| `POST /v1/calls/classify` | Post-call analysis: label a finished call against your objective |

**Adversarial QA, built in.** `POST /v1/qa/suite` generates a bespoke test
suite from your agent's own objective, plays each scenario as a mock call
against your real configuration, and judges every call twice — pass/fail on
the scenario's assertion **and** an SSR grade (the judge picks one of five
nominal levels, *poorly/ok/good/great/perfectly*, mapped deterministically to
a score + distribution). `POST /v1/qa/run` plays every scenario A/B —
supervised vs unsupervised — and reports the watcher's measured lift. How
this stacks up against Hamming, Coval, Roark, Cekura, and the rest of the
2026 voice-QA field: [gitbook/voice-qa-landscape.md](gitbook/voice-qa-landscape.md).

<details>
<summary><b>Python</b></summary>

```python
import httpx

API, KEY = "https://api.labs.supafone.ai", os.environ["SUPAFONE_LABS_API_KEY"]

r = httpx.post(f"{API}/v1/oracle/complete",
    headers={"Authorization": f"Bearer {KEY}"},
    json={"model": "supafone-labs-oracle", "messages": [...]})
directive = r.json()["text"]                     # the silent coaching line

audio = httpx.post(f"{API}/v1/tts",
    headers={"Authorization": f"Bearer {KEY}"},
    json={"voice": "supafone-labs-calm-en", "text": "Right away."}).content
```
</details>

<details>
<summary><b>TypeScript</b></summary>

```ts
const API = "https://api.labs.supafone.ai";
const auth = { Authorization: `Bearer ${process.env.SUPAFONE_LABS_API_KEY}` };

const { text } = await fetch(`${API}/v1/oracle/complete`, {
  method: "POST",
  headers: { ...auth, "Content-Type": "application/json" },
  body: JSON.stringify({ model: "supafone-labs-oracle", messages: [...] }),
}).then(r => r.json());

// live multilingual STT — language-tagged Results, 10 languages, code-switching
const ws = new WebSocket(`${API.replace("https","wss")}/v1/stt/live` +
  `?api_key=${KEY}&language=multi&encoding=linear16&sample_rate=16000`);
```
</details>

Full reference with every endpoint, WebSocket framing, and error shapes:
[**docs**](https://labs.supafone.ai/docs.html) · interactive
[OpenAPI](https://api.labs.supafone.ai/docs).

## Pricing

| | |
|---|---|
| **Signup** | 5 free minutes, no card |
| **Developer** | $49/mo → 300 included Supafone minutes; then $0.14/min |
| **Growth** | $249/mo → 2,500 included Supafone minutes; then $0.11/min |
| **Scale** | $999/mo → 12,000 included Supafone minutes; then $0.085/min |
| **Managed numbers** | $1.25-$1.50/number-month depending on tier |
| **Metering** | oracle call = 1s · TTS ≈ seconds of speech · live STT = session time |
| **Self-host** | free forever — the gateway (`cloud/`) is in this repo, MIT |

Every billed second is itemized in [`/v1/logs`](https://labs.supafone.ai/console.html).
The live pricing contract is exposed at [`/v1/pricing`](https://api.labs.supafone.ai/v1/pricing)
and rendered at [labs.supafone.ai/pricing.html](https://labs.supafone.ai/pricing.html).
BYO vendor keys always win when present — leaving the cloud is deleting one
environment variable.

## Works with every voice platform

Speech-to-speech models, STT→LLM→TTS pipelines, frameworks, and raw speech
engines each get the injection channel they actually have:

| Platform | Kind | Watcher delivery |
|---|---|---|
| Supafone · Ultravox | managed / S2S | deferred `user_text_message` |
| Vapi | agent platform | system `add-message` via live-call `controlUrl` |
| OpenAI Realtime · Inworld Realtime | realtime S2S | system `conversation.item.create` |
| xAI Grok | realtime S2S | per-response `response.create.instructions` |
| Gemini Live | realtime S2S | `clientContent` user turn (system is invalid mid-session) |
| Retell | custom-LLM WS | system entry in your owned LLM context |
| ElevenLabs Agents | agent platform | `contextual_update` |
| Deepgram Voice Agent | agent platform | `UpdatePrompt` |
| Pipecat · LiveKit Agents | frameworks | context frame / chat-context append |
| Bland | observation only | no documented prompt-injection control |
| Cartesia Line | custom hook | no action until your agent handles a custom event |
| Anything else | webhook | `GenericWebhookAdapter`, configurable |

The release gate covers **fourteen public runtimes** from provider event through
Watcher decision to exact delivery payload. Credentialed probes separately send
real controls and wait for provider acceptance; missing credentials skip rather
than pass. [docs/providers.md](docs/providers.md) has the current contract and
test matrix. Telephony is
transport-agnostic: Twilio, Telnyx, SignalWire, Vonage, Plivo, LiveKit SIP,
Jambonz, FreeSWITCH/Asterisk, and SIPREC forks all feed the same tap
([SIP matrix](https://labs.supafone.ai/docs.html#sip)).

Runnable integrations for every permutation live in [`examples/`](examples/).

## Live multilingual transcription

Callers switch languages mid-sentence; the tap keeps up. Deepgram nova-3
`language=multi` code-switches live across en/es/fr/de/hi/ru/pt/ja/it/nl,
every utterance arrives language-tagged, and the coaching comes back in the
caller's language — Spanish callers get Spanish guardrails, silently, mid-call.

```python
from supafone_labs.stt import MultilingualCallTap, recommended_setup

recommended_setup("vapi")                       # -> use Vapi's transcripts, skip the tap
recommended_setup("ultravox", multilingual=True)  # -> tap becomes the language authority

tap = MultilingualCallTap(brain, session_id=call_sid)   # any SIP/audio fork
await tap.feed(track="inbound", payload_b64=frame)
```

One rule prevents every bad combination: **exactly one transcript source per
call** — `recommended_setup()` picks it, so you never double-ingest or
double-pay. With `SUPAFONE_LABS_API_KEY` set and no Deepgram account, the tap
routes through the hosted proxy automatically.

## Pick your model. Write your prompts.

```python
brain = supafone_labs.SupafoneLabs(
    provider="ultravox",
    oracle_model="claude-sonnet-4-6",     # provider auto-inferred (Anthropic/OpenAI/xAI/hosted)
    oracle_instructions="Coach for a bilingual intake desk. Empathy before logistics.",
)

models = await supafone_labs.discover_oracle_models()   # live vendor catalogs, cached hourly
```

Model routing is prefix-based and the catalogs are fetched from vendor APIs at
runtime — **a model released tomorrow works today**, no package update. The
static table in `config.py` is an offline fallback only.

## Built for production

- **Degrade-safe by construction** — the oracle runs behind a timeout off the
  hot path; a stalled LLM, a dead STT socket, or a failed TTS backend can never
  take down the call it's shadowing. The TTS chain fails downward
  (hosted → your keys → offline audio); the tap no-ops without credentials.
- **Auditable** — every whispered instruction is in `/v1/logs` with a
  timestamp and its exact cost. No black box.
- **Tested like infrastructure** — 200+ offline tests (every adapter's parse,
  injection compile, and capability honesty; end-to-end facade runs per
  provider; billing; tiering) plus live contract checks against Deepgram,
  Ultravox, ElevenLabs, Cartesia, and Inworld.
- **No lock-in** — MIT package, MIT gateway. Self-host the whole cloud:
  `cd cloud && uvicorn app:app`.

## The research behind it

The architecture is an assembly of five peer-reviewed threads — dual-process
talker/reasoner agents (DeepMind's [Talker-Reasoner](https://arxiv.org/abs/2410.08328)),
the evidence that models [can't reliably self-correct](https://arxiv.org/abs/2310.01798)
(hence an *external* supervisor), generator/verifier splits
([Cobbe 2021](https://arxiv.org/abs/2110.14168), [Lightman 2023](https://arxiv.org/abs/2305.20050),
[Baker 2025](https://arxiv.org/abs/2503.11926)), inference-time multi-model oversight
(Sakana AI's [AB-MCTS](https://arxiv.org/abs/2503.04412)), and feedback-driven prompt
optimization ([OPRO](https://arxiv.org/abs/2309.03409), [DSPy](https://arxiv.org/abs/2310.03714),
[TextGrad](https://arxiv.org/abs/2406.07496)). All 22 citations, verified and annotated:
[**the research page**](https://labs.supafone.ai/research.html), and the full synthesis —
meta-analysis plus the formal runtime treatment — is the
[**whitepaper (PDF)**](https://labs.supafone.ai/whitepaper.pdf)
([LaTeX source](paper/whitepaper.tex)).

The QA methodology has its own paper: **Grading the Call** — objective-derived
adversarial suites, SSR nominal-scale judging with deterministic score
distributions, and supervision-lift A/B testing, situated against the
2025–2026 voice-QA landscape (Coval, Hamming, Roark, Cekura, Bluejay,
platform-native suites, τ-bench, VoiceBench) —
[PDF](paper/voice-qa.pdf) ([LaTeX source](paper/voice-qa.tex)).

## Repo layout

```
src/supafone_labs/     the package — facade, oracle, runtime + 14 audited runtimes, tts, stt, tiers
cloud/              Supafone Labs Cloud — the hosted gateway (FastAPI)
landing/            the website (landing, get-key, console, docs)
examples/           one runnable integration per platform + TypeScript client
tests/              200+ offline tests · live contract checks (pytest -m live)
docs/               provider capability matrix + quickstart
```

## Development

```bash
make install                  # editable install + dev tools
make test                     # offline suite (live tests skip without keys)
make test-provider-contracts  # 14-runtime event -> Watcher -> exact-action gate
make test-live-injection      # real controls; missing credentials are skips
make lint                     # ruff
cd cloud && uvicorn app:app --reload    # run the gateway locally
```

## Security

Keys are bearer credentials — treat `sl_live_…` like a password. The gateway
stores no call audio; logs keep a 240-char excerpt per request (last 1,000 per
key) for your own auditability. Report vulnerabilities via
[SECURITY.md](SECURITY.md).

## License

MIT © 2026 Sam Savage. Free tier is free forever; the cloud exists because one
key that runs everything is more convenient than five vendor accounts.
