<div align="center">

<img src="gitbook/.gitbook/assets/supafone-logo.png" alt="Supafone" width="112" height="112" />

# Supafone Labs

**One speech-to-speech harness. Build an agent once, then choose its speaking
model.** Agent Factory connects supported S2S models to shared prompts, tools,
stages, and browser/phone delivery through Python, TypeScript, and REST.

[![CI](https://github.com/samthedataman/supafone-labs/actions/workflows/ci.yml/badge.svg)](https://github.com/samthedataman/supafone-labs/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/supafone-labs)](https://pypi.org/project/supafone-labs/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://pypi.org/project/supafone-labs/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![API](https://img.shields.io/badge/cloud%20API-live-3fd0c9)](https://api.labs.supafone.ai/healthz)

[**Website**](https://labs.supafone.ai) ·
[**Docs**](https://labs.supafone.ai/docs/) ·
[**Shared S2S interface**](gitbook/unified-s2s.md) ·
[**Agent Factory**](https://app.supafone.ai/app/agents) ·
[**Get a free API key**](https://labs.supafone.ai/console.html?mode=register) ·
[**API reference**](https://api.labs.supafone.ai/docs)

</div>

---

## Start here: the S2S harness

Agent Factory creates the agent; the harness runs its selected speaking model
with supported tools, stages, and browser or phone delivery. The exported
`SupafoneS2S` superclass gives Python and TypeScript one interface for five
provider families: **Ultravox, OpenAI, Gemini, Grok, and Smallest AI Hydra**.
Ultravox remains the default. The native catalog adds six choices: OpenAI
`gpt-realtime-2.1` and `gpt-live-1`, Google `gemini-3.1-flash-live-preview`,
xAI `grok-voice-latest`, and Smallest AI `hydra-v1.0` and `hydra-v1.1`.

Use one Supafone application key. A configured platform key supplies the
selected model unless the account has an encrypted BYOK override. Check the
provider's runtime status before launch; catalog support and key presence do
not establish model access or successful carrier calls.

```ts
import { Supafone, HydraS2S, OpenAIS2S } from "supafone-labs";

const sf = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN! });
const hydra = new HydraS2S(sf, { model: "hydra-v1.1", voice: "maya" });
await hydra.create({
  agentKey: "intake",
  name: "Intake",
  description: "Understand the request and book the right next step.",
});

// Switch the same agent for its next call, then preview the saved selection.
const openai = new OpenAIS2S(sf, { model: "gpt-realtime-2.1", voice: "marin" });
await openai.apply("intake");
const preview = await openai.testCall("intake");
```

`create`, `apply`, and `testCall` (Python `test_call`) work across all five
provider classes. Preview does not apply a selection automatically. Switching
keeps the agent, phone assignment, custom stage plan, team and configured tools.
All five speaking families use the same shared call runtime. Phone delivery supports
Supafone-managed, Twilio, Telnyx, Plivo, and SIP with separate carrier setup.

All five hosted speaking families support Supervisor coaching when enabled
and configured. Native models request guidance through `check_guidance`;
Hydra supplies labeled model-reported context, not transcripts.

The shared runtime adds generated/custom stages, saved facts, tool receipts,
Manager reasoning and specialist consultations. Native calls support public
widgets, opt-in recording, configured carrier controls and opt-in native model
handoff. Handoff opens a replacement session; it is not seamless provider
resumption. Hydra has no live transcript stream. External TTS and the existing
language/voice profile router remain on the compatible Ultravox path.
`UltravoxS2S` selects that default; omitting `realtime` does the same.

[Shared runtime, Manager and teams](gitbook/shared-agent-runtime.md) documents
request fields, server-enforced gates, reasoning budgets, recording and exact
capability limits. These are implementation contracts, not evidence that every
model/carrier combination has passed a live deployment test.

[Shared Python and TypeScript interface](gitbook/unified-s2s.md) ·
[Quickstart](gitbook/quickstart.md) · [Native runtime contract](gitbook/realtime-agent-factory.md) ·
[Managed keys and BYOK](gitbook/byok-providers.md) · [Framework coverage](gitbook/framework-support.md)

## Keep custom TTS alongside native S2S

The existing **Ultravox + custom TTS** phone agent is part of the shared
`SupafoneS2S` interface. Use `UltravoxS2S` with the agent's `voice` settings for
compatible Cartesia, ElevenLabs, Inworld, or Ultravox catalog voices. Use the
other provider classes for native S2S with each model's own voice list.

External TTS is specific to compatible runtimes. Deepgram previews and custom
SDK synthesis do not automatically enable a hosted phone-call integration.
[Compare voice-output choices and see working examples](gitbook/voice-output-modes.md).

## Supafone Supervisor: supervise an existing stack

Supafone Supervisor is a separate offering: a second AI runs beside the realtime
agent, observes the live conversation off the latency-critical audio path, and
silently corrects the agent when it detects tool failures, unsafe claims,
language changes, missed intent, or a broken workflow. If the Supervisor has
nothing useful to add—or cannot respond in time—the call continues unchanged.

All five hosted speaking families can enable Supervisor coaching through both
SDKs. Standalone framework adapters have their own delivery capabilities:

```python
from supafone_labs import Supafone

supafone = Supafone(api_key="sl_live_...")
```

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN! });
```

Agent Factory customers can use Supafone's managed Supervisor models without
another vendor key when the deployment has the managed credentials configured:

```ts
const agent = await supafone.labs.agents.createInbound({
  name: "Northline intake",
  supervisor: {
    mode: "managed",
    model: "supafone-supervisor", // or supafone-supervisor-pro
  },
});
```

Or bring the independent reasoning model already approved by your team. BYOK
Supervisor supports six explicit first-party provider contracts:

| Provider | `provider` | Default model | Environment variable |
| --- | --- | --- | --- |
| Claude | `anthropic` | `claude-haiku-4-5-20251001` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai` | `gpt-5-mini` | `OPENAI_API_KEY` |
| Gemini | `gemini` | `gemini-2.5-flash` | `GEMINI_API_KEY` |
| OpenRouter | `openrouter` | `anthropic/claude-haiku-4.5` | `OPENROUTER_API_KEY` |
| Groq | `groq` | `llama-3.1-8b-instant` | `GROQ_API_KEY` |
| Cerebras | `cerebras` | `gpt-oss-120b` | `CEREBRAS_API_KEY` |

```python
import os
from supafone_labs import Supafone

supafone = Supafone(api_key=os.environ["SUPAFONE_API_KEY"])
agent = supafone.labs.agents.create_inbound({
    "name": "Gemini supervised intake",
    "supervisor": {
        "enabled": True,
        "mode": "byok",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "api_key": os.environ["GEMINI_API_KEY"],
    },
})
```

```ts
const agent = await supafone.labs.agents.createInbound({
  name: "OpenAI supervised intake",
  supervisor: {
    enabled: true,
    mode: "byok",
    provider: "openai",
    model: "gpt-5-mini",
    apiKey: process.env.OPENAI_API_KEY!,
  },
});
```

Keys are encrypted before storage and never returned. The complete
[managed/BYOK guide](gitbook/supervisor-models.md) includes Claude, OpenAI, Gemini,
OpenRouter, Groq, and Cerebras examples for Python, TypeScript, REST, and CLI.

Already running Vapi, Retell, Ultravox, OpenAI Realtime, LiveKit, Pipecat, or
another stack? Keep it. Feed provider events into the Supervisor and deliver its
canonical silent directive through the matching adapter.

**Read this first:** [Supafone Supervisor framework](gitbook/supafone-supervisor.md) ·
[production problems it solves](gitbook/production-voice-ai-challenges.md) ·
[framework support](gitbook/framework-support.md) ·
[programmable directives](gitbook/programmable-supervisor-directives.md) ·
[live voice catalog](gitbook/voice-catalog-and-selection.md) ·
[adversarial QA](gitbook/voice-qa-landscape.md) ·
[MCP setup](mcp/README.md)

```python
import supafone_labs

brain = supafone_labs.supercharge(my_agent)   # that's the whole integration
```

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN! });

const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake",
  name: "Northline intake",
  assistantName: "Maya",
  description: "Answer new inquiries, understand the request, and book the right next step.",
  websiteUrl: "https://northline.example",
  number: { search: { areaCode: "415" } },
  labs: { enabled: true, model: "gemma" },
});

// Lifecycle methods use agent_key. Corpus and WebRTC methods use agent.id.
await supafone.labs.agents.update(agent.agent.agent_key!, {
  greeting: "Thanks for calling Northline. How can I help?",
});
await supafone.labs.agents.syncKnowledge(
  agent.agent.id!,
  { websiteUrl: "https://northline.example" },
);
const browserCall = await supafone.labs.agents.startWebRtcCall(agent.agent.id!);
```

Multilingual Agent Factory calls are also opt-in and default off:

```ts
await supafone.labs.agents.createInbound({
  agentKey: "bilingual-intake",
  name: "Bilingual intake",
  languageVoiceRouting: true,
  routingLanguages: ["en-US", "es-MX"],
});
```

Only the boolean and optional language/voice preferences are public. Supafone
keeps detection, voice resolution, and live call transitions in the hosted
backend.

The first configured language owns the greeting. A non-English primary
greeting is translated during provisioning; see the
[complete public guide](gitbook/live-language-voice-routing.md).

Outbound agents can also opt into bounded phone-tree navigation:

```python
agent = supafone.labs.agents.create_outbound({
    "name": "Benefits verification",
    "outbound_call_mode": {
        "enabled": True,
        "max_duration_seconds": 180,
        "max_keypresses": 12,
    },
})
```

The same contract covers Supafone-managed, Twilio, Telnyx, Plivo,
SignalWire, and SIP/BYOC transports. Adapter capabilities are checked
fail-closed; a carrier name alone never implies that DTMF navigation is ready.
See [Outbound IVR Call Mode](gitbook/outbound-ivr-call-mode.md).

The TypeScript package is also the canonical client for the Supafone hosted
agent API at `https://api.supafone.ai/api/v1/labs`. The default path buys and
routes Supafone-managed numbers, so developers do not need to create Twilio,
Ultravox, Cartesia, Inworld, ElevenLabs, or Deepgram accounts just to ship an
agent. BYOK remains available when a team already owns those provider accounts.

### Describe the job once

Agent Factory now turns that `description` into the complete prompt and staged
call plan that the runtime actually executes. Developers do not need a second
Haiku/Anthropic key, and customers do not have to accept a black-box prompt:

```ts
const plan = await supafone.generateCallStages({
  name: "Warm lead caller",
  description: "Call consented leads, understand fit, and book a demo without pressure.",
  direction: "outbound",
  stageCount: 5,
});

// Preview, edit, approve, or version ordinary JSON.
console.log(plan.call_stages);
```

The practical advantage is simple: less prompt plumbing for the developer and
a calmer, more consistent conversation for the customer. Stages remember where
the call is, tool claims require real tool confirmation, outbound opt-outs are
explicit, and the safe template keeps creation available if the hosted planner
is temporarily unavailable.

## S2S Agent Factory and Supafone Supervisor

The native Agent Factory creates an agent for the shared S2S harness. Choose
its speaking model while retaining the configured tools, custom stages, team, and
browser or carrier transport. Supafone Supervisor can coach all five hosted
speaking families and supported existing stacks. Native models request bounded
guidance through `check_guidance`; Hydra supplies model-reported context, not
transcripts. The managed Ultravox runtime keeps its deferred guidance delivery
and compatible external TTS/language profiles.

The supervisor is model agnostic by construction. Provider adapters normalize
each stack into one call-state contract and compile one abstract directive back
into the provider's supported control channel. The speaking model, supervisor
model, carrier, STT, and TTS can therefore evolve independently.

Managed is the default. BYOK is available when the customer already owns
provider accounts or needs provider-specific controls. Keep the BYOK lanes
separate:

| BYOK lane | What it covers | Examples |
| --- | --- | --- |
| Agent/provider stack | The realtime agent or model runtime | Use any of the [14 audited runtime adapters](gitbook/framework-support.md) |
| Telephony | Carrier, trunk, and phone-network credentials | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks |
| TTS | Voice rendering and voice-clone/provider credentials | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS |
| STT | Live transcription and language authority | Deepgram or provider-native transcripts |
| Supervisor model | The model that produces Supervisor directives | Supafone managed, Claude, OpenAI, Gemini, OpenRouter, Groq, Cerebras |

Those lanes can be mixed. A team can use Supafone-managed telephony with BYOK
TTS, or BYOK Twilio/Telnyx with the managed supervisor, or bring the full
stack and only use Supafone for self-healing supervision and logs.
See the [BYOK provider details](gitbook/byok-providers.md) for the complete credential and transport matrix.

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

**Supafone Labs is the supervisor.** A separate reasoning loop that runs *beside* the
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

**And when the supervisor fails?** Nothing happens. It runs behind a timeout,
off the hot path; a stalled Supervisor yields no note and the call proceeds exactly
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

**1 — Get a key** (five account-wide managed-runtime minutes, no card):

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
# result.actions -> the compiled native whisper (or [] when supervision is quiet)
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

With the key set, the Supervisor, TTS, and live multilingual STT all run on
Supafone Labs' hosted infrastructure. Without it, everything runs on **your own
vendor keys** — or fully offline on deterministic fakes. Same code, all three
modes.

**3 — Watch it work** in the [console](https://labs.supafone.ai/console.html):
your balance, usage, and an auditable log of every instruction your second
mind whispered.

## Native realtime Agent Factory models

The hosted Agent Factory accepts one `realtime` selection for direct speech-to-
speech browser previews and managed or BYO phone agents:

| Provider | Model |
| --- | --- |
| OpenAI | `gpt-realtime-2.1` |
| OpenAI | `gpt-live-1` |
| Google | `gemini-3.1-flash-live-preview` |
| xAI | `grok-voice-latest` |
| Smallest AI | `hydra-v1.0` |
| Smallest AI | `hydra-v1.1` |

The selection is available from both the Python and TypeScript clients and from
the [Supafone agent dashboard](https://app.supafone.ai/app/agents). Every model exposes the same five phone transports:
Supafone-managed, BYO Twilio, BYO Telnyx, BYO Plivo, and BYO SIP. The native path
uses the shared generated/custom stage plan with server-enforced transitions
and tool permissions. A configured platform model key or account BYOK key,
plus managed or BYO carrier readiness, is required for a live call.

```ts
const agent = await supafone.labs.agents.createInbound({
  name: "Northline realtime intake",
  realtime: {
    provider: "google",
    model: "gemini-3.1-flash-live-preview",
    voice: "Puck",
  },
});
```

```python
agent = supafone.labs.agents.create_outbound(
    name="Northline realtime follow-up",
    realtime={
        "provider": "xai",
        "model": "grok-voice-latest",
        "voice": "eve",
    },
)
```

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
- Supafone Supervisor live guidance and call coaching.

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
      "command": "python3.12",
      "args": ["<repo>/mcp/supafone_mcp.py"],
      "env": {
        "SUPAFONE_TOKEN": "sl_live_..."
      }
    }
  }
}
```

`<repo>` is the absolute path to the cloned **public `supafone-labs` repository**.
After changing this file, fully restart the MCP client so it refreshes
`tools/list`. A correct connection advertises `start_call_and_watch`; a short
models/usage-only list means Claude is still launching a different command.

Two independent auth lanes — set the ones you use:

| Lane | Env | Unlocks |
| --- | --- | --- |
| One-key setup | Linked `SUPAFONE_TOKEN=sl_live_...` | Agents, campaigns, guarded real calls, monitoring, numbers, Labs logs/usage/voices |
| Explicit fallback | `SUPAFONE_EMAIL` + `SUPAFONE_PASSWORD`, or separate `SUPAFONE_API_KEY` / `SUPAFONE_LABS_API_KEY` | Same surfaces when one-key linking is unavailable |

The server logs in lazily with the email/password and transparently re-logs-in
when the token expires — a long Claude session never goes stale.

### What Claude can do with it

- **Campaigns end to end** — `create_campaign`, `apply_campaign_preset`
  (built-in playbooks or your saved custom presets), `add_campaign_recipients`
  (consented leads), `launch_campaign` / `pause_campaign`, `update_campaign`
  (scripts, cadence, settings — including the e-sign document config).
- **Real phone calls** — `start_call_and_watch` (or `call_from_owned_agent`)
  dials through your configured calling provider, bridges your voice agent onto
  the line, and returns a secret-free authenticated dashboard link for the live
  call. `list_voice_agents` picks the agent.
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
`supafone-labs` (npm) — `client.campaigns.*`, `callFromAgent()`, and
`startWebRtcCall()` for browser voice sessions without a phone number.

## How it works

```
                      ┌─────────────────────────────────────────────┐
  your live call ────▶│  TAP        13 platform adapters +          │
  (any platform)      │             Deepgram nova-3 multilingual    │
                      │             STT for audio-only stacks       │
                      ├─────────────────────────────────────────────┤
                      │  THINK      belief state + Supervisor       │
                      │             (off the latency path, timeout- │
                      │             bounded, degrade-safe)          │
                      ├─────────────────────────────────────────────┤
  silent whisper ◀────│  WHISPER    compiled to the platform's      │
  (native channel)    │             native control — never spoken   │
                      └─────────────────────────────────────────────┘
```

## The Cloud API

One key fronts the whole stack — hosted Supervisor models, four TTS engines under
one voice namespace, and live multilingual transcription. Billed by the
minute; every request itemized.

| Endpoint | What it does |
|---|---|
| `POST /v1/signup` | Self-serve key — five account-wide managed-runtime minutes, no card |
| `POST /v1/supervisor/complete` | Hosted Supervisor completion |
| `GET  /v1/models` | Live model catalog, fetched hourly from vendors — **never stale** |
| `POST /v1/tts` | Managed Cartesia TTS by default; other engines are explicit BYOK choices |
| `GET  /v1/voices` | The hosted voice catalog |
| `POST /v1/stt` | Prerecorded transcription (nova-3, 10-language code-switching) |
| `WS   /v1/stt/live` | Live streaming STT — the multilingual tap, zero Deepgram account |
| `GET  /v1/usage` | Today's request counts |
| `GET  /v1/billing/balance` | Minutes remaining + top-up links |
| `POST /v1/billing/checkout` | Server-authored plan, credit, or paid-number Stripe Checkout |
| `GET  /v1/billing/checkout/{session_id}` | Poll payment and number-entitlement readiness |
| `POST /v1/billing/portal` | Authenticated Stripe Customer Portal link |
| `GET  /v1/logs` | The audit trail: every whisper, timestamped and billed |
| `POST /v1/qa/generate` | Adversarial test scenarios generated from your agent's own prompt |
| `POST /v1/qa/suite` | One-call auto QA suite: mock calls vs your real config, pass/fail + SSR grades |
| `POST /v1/calls/classify` | Post-call analysis: label a finished call against your objective |

The five-minute allowance belongs to the account, not each key or agent.
Managed WebRTC and PSTN calls reserve available seconds atomically before the
provider session starts, so concurrent calls cannot spend the same balance.
Settlement bills connected time and refunds the unused hold. A depleted account
receives a structured HTTP 402 with `detail.code=managed_minutes_exhausted` and
`detail.checkout_endpoint=/v1/billing/checkout`; complete the server-authored
Stripe Checkout and retry the original call.

The hosted product API also exposes the safe shared developer-number inventory
at `GET https://api.supafone.ai/api/v1/labs/phone-numbers/pool`. Its stream uses
a short-lived pool-only token and includes only numbers an operator explicitly
enrolled for developer use, never customer production lines.

**Adversarial QA, built in.** `POST /v1/qa/suite` generates a bespoke test
suite from your agent's own objective, plays each scenario as a mock call
against your real configuration, and judges every call twice — pass/fail on
the scenario's assertion **and** an SSR grade (the judge picks one of five
nominal levels, *poorly/ok/good/great/perfectly*, mapped deterministically to
a score + distribution). `POST /v1/qa/run` plays every scenario A/B —
supervised vs unsupervised — and reports the supervisor's measured lift. How
this stacks up against Hamming, Coval, Roark, Cekura, and the rest of the
2026 voice-QA field: [gitbook/voice-qa-landscape.md](gitbook/voice-qa-landscape.md).

<details>
<summary><b>Python</b></summary>

```python
import httpx

API, KEY = "https://api.labs.supafone.ai", os.environ["SUPAFONE_LABS_API_KEY"]

r = httpx.post(f"{API}/v1/supervisor/complete",
    headers={"Authorization": f"Bearer {KEY}"},
    json={"model": "supafone-supervisor", "messages": [...]})
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

const { text } = await fetch(`${API}/v1/supervisor/complete`, {
  method: "POST",
  headers: { ...auth, "Content-Type": "application/json" },
  body: JSON.stringify({ model: "supafone-supervisor", messages: [...] }),
}).then(r => r.json());

// live multilingual STT — language-tagged Results, 10 languages, code-switching
const ws = new WebSocket(`${API.replace("https","wss")}/v1/stt/live` +
  `?api_key=${KEY}&language=multi&encoding=linear16&sample_rate=16000`);
```
</details>

Full reference with every endpoint, WebSocket framing, and error shapes:
[**docs**](https://labs.supafone.ai/docs/) · interactive
[OpenAPI](https://api.labs.supafone.ai/docs).

## Pricing

| | |
|---|---|
| **Signup** | Five account-wide managed-runtime minutes, no card |
| **Developer** | $49/mo → 300 included Supafone minutes; then $0.14/min |
| **Growth** | $249/mo → 2,500 included Supafone minutes; then $0.11/min |
| **Scale** | $999/mo → 12,000 included Supafone minutes; then $0.085/min |
| **Managed numbers** | $1.25-$1.50/number-month depending on tier |
| **Metering** | Supervisor work, TTS speech, and live STT are itemized in usage logs |
| **Open-source SDK** | MIT runtime, adapters, replay, and local BYOK integrations; hosted Supafone Cloud remains a managed service |

Every billed second is itemized in [`/v1/logs`](https://labs.supafone.ai/console.html).
The live pricing contract is exposed at [`/v1/pricing`](https://api.labs.supafone.ai/v1/pricing)
and rendered at [labs.supafone.ai/pricing.html](https://labs.supafone.ai/pricing.html).
BYO vendor keys always win when present — leaving the cloud is deleting one
environment variable.

## Audited framework coverage

Speech-to-speech models, STT→LLM→TTS pipelines, frameworks, and raw speech
engines each get the injection channel they actually have:

| Platform | Kind | Supervisor delivery |
|---|---|---|
| Supafone · Ultravox | managed / S2S | deferred `user_text_message` |
| Vapi | agent platform | system `add-message` via live-call `controlUrl` |
| OpenAI Realtime · Inworld Realtime | realtime S2S | system `conversation.item.create` |
| xAI Grok | realtime S2S | per-response `response.create.instructions` |
| Gemini Live | observation adapter | Ordinary `clientContent` user context; no hidden mid-call guidance |
| Retell | custom-LLM WS | system entry in your owned LLM context |
| ElevenLabs Agents | agent platform | `contextual_update` |
| Deepgram Voice Agent | agent platform | `UpdatePrompt` |
| Pipecat · LiveKit Agents | frameworks | context frame / chat-context append |
| Bland | observation only | no documented prompt-injection control |
| Cartesia Line | custom hook | no action until your agent handles a custom event |
| Anything else | webhook | `GenericWebhookAdapter`, configurable |

The release gate covers **fourteen public runtimes** from provider event through
Supervisor decision to exact delivery payload. Credentialed probes separately send
real controls and wait for provider acceptance; missing credentials skip rather
than pass. [docs/providers.md](docs/providers.md) has the current contract and
test matrix, while the
[GitBook framework matrix](gitbook/framework-support.md) explains support depth
and adjacent TTS, STT, telephony, LLM, prompt, and SDK layers. Telephony is
transport-agnostic: Twilio, Telnyx, SignalWire, Vonage, Plivo, LiveKit SIP,
Jambonz, FreeSWITCH/Asterisk, and SIPREC forks all feed the same tap
([SIP matrix](https://labs.supafone.ai/docs/#sip)).

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
    supervisor_model="claude-sonnet-4-6",
    supervisor_instructions="Coach for a bilingual intake desk. Empathy before logistics.",
)

models = await supafone_labs.discover_supervisor_models()
```

Model routing is prefix-based and the catalogs are fetched from vendor APIs at
runtime — **a model released tomorrow works today**, no package update. The
static table in `config.py` is an offline fallback only.

## Built for production

- **Degrade-safe by construction** — the Supervisor runs behind a timeout off the
  hot path; a stalled LLM, a dead STT socket, or a failed TTS backend can never
  take down the call it's shadowing. The TTS chain fails downward
  (hosted → your keys → offline audio); the tap no-ops without credentials.
- **Auditable** — every whispered instruction is in `/v1/logs` with a
  timestamp and its exact cost. No black box.
- **Tested like infrastructure** — 200+ offline tests (every adapter's parse,
  injection compile, and capability honesty; end-to-end facade runs per
  provider; billing; tiering) plus live contract checks against Deepgram,
  Ultravox, ElevenLabs, Cartesia, and Inworld.
- **No SDK lock-in** — the runtime, adapters, replay, and local BYOK paths are
  MIT licensed. Supafone-managed telephony, billing, and hosted model services
  remain managed infrastructure.

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
meta-analysis plus the formal runtime treatment — is available as the
[**whitepaper (PDF)**](https://labs.supafone.ai/whitepaper.pdf) and the
[versioned documentation source](gitbook/research-paper.md).

The QA methodology has its own paper: **Grading the Call** — objective-derived
adversarial suites, SSR nominal-scale judging with deterministic score
distributions, and supervision-lift A/B testing, situated against the
2025–2026 voice-QA landscape (Coval, Hamming, Roark, Cekura, Bluejay,
platform-native suites, τ-bench, VoiceBench) — read the
[versioned QA landscape and methodology](gitbook/voice-qa-landscape.md).

## Repo layout

```
src/supafone_labs/  Python SDK, CLI, Supervisor, runtime adapters, TTS, STT
sdk-ts/             TypeScript SDK
mcp/                MCP server and tool contracts
examples/           runnable integrations
tests/              offline and credentialed contract checks
docs/               MkDocs source
gitbook/            GitBook source
```

## Development

```bash
make install                  # editable install + dev tools
make test                     # offline suite (live tests skip without keys)
make test-provider-contracts  # 14-runtime event -> Supervisor -> exact-action gate
make test-live-injection      # real controls; missing credentials are skips
make lint                     # ruff
```

## Security

Keys are bearer credentials — treat `sl_live_…` like a password. The gateway
stores no call audio; logs keep a 240-char excerpt per request (last 1,000 per
key) for your own auditability. Report vulnerabilities via
[SECURITY.md](SECURITY.md).

## License

MIT © 2026 Sam Savage. The SDK is open source; Supafone-managed runtime usage
is metered because it operates the hosted models, speech, telephony, billing,
and artifact infrastructure behind one key.
