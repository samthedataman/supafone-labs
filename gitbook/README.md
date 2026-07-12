<p align="center">
  <img src=".gitbook/assets/supafone-logo.png" alt="Supafone" width="88" height="88" />
</p>

# 📞 Supafone Labs

🐍 [Python — `pip install "supafone-labs[all]"`](https://pypi.org/project/supafone-labs/) ·
🟦 [TypeScript — `npm i supafone-labs`](https://www.npmjs.com/package/supafone-labs) ·
⭐ [GitHub — samthedataman/supafone](https://github.com/samthedataman/supafone) ·
🌐 [labs.supafone.ai](https://labs.supafone.ai) ·
📄 [Research papers](https://labs.supafone.ai/research.html)

## The developer pain we solve

Shipping a production voice agent today means gluing together seven different
vendors before you write a line of product logic. **Nobody wants to do this
themselves:**

| Pain point | What it takes alone | With Supafone Labs |
| --- | --- | --- |
| **Phone numbers** | Twilio account, number search, webhooks, compliance | `number: { search: { areaCode: "415" } }` |
| **TTS / STT keys** | Cartesia + Deepgram + ElevenLabs accounts, voice tuning | Managed voices, one namespace, hosted STT with 10-language code-switching |
| **Knowledge / RAG** | Vector DB, chunking, retrieval tuning | `tools: { firmKnowledge: true }` |
| **Tool calls** | Per-platform tool schemas, verification plumbing | Built-in stages + tools with verified ground truth |
| **Self-healing** | A second supervision stack nobody budgets for | `labs: { enabled: true }` — the watcher whispers silent corrections mid-call |
| **Call classification** | Post-call pipeline, judge prompts, label storage | `post_call_analysis=True` — every call auto-labeled against your objective |
| **Testing / QA** | A separate QA vendor and integration project | `qa.suite()` — adversarial suite generated from your agent's own prompt, SSR-graded |

The whole thing is **five lines of code**:

```ts
import { Supafone } from "supafone-labs";
const supafone = new Supafone({ apiKey: process.env.SUPAFONE_LABS_API_KEY!, postCallAnalysis: true });
const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake", name: "Northline intake",
  number: { search: { areaCode: "415" } }, labs: { enabled: true },
});
```

That's a live phone number, a staged multi-turn agent, managed voice, tools,
recordings, transcripts, a self-healing watcher on the line, automatic
post-call classification — and an adversarial QA suite one call away
(`await supafone.qa.suite()`), graded with
[SSR nominal scoring](voice-qa-landscape.md) and all that fancy jazz.

## Every framework, one framework

The voice-AI substrate is fragmented on purpose: speech-to-speech models
(GPT Realtime, Grok, Ultravox), STT→LLM→TTS pipelines, agent platforms
(**Vapi, Retell, Bland, LiveKit, Pipecat**), raw speech components (Deepgram,
Cartesia, ElevenLabs, Inworld), and telephony carriers (Twilio, Telnyx, Plivo,
SignalWire, SIP) each expose different event vocabularies and different —
sometimes no — control channels. Every one of those vendors solves *their*
layer; none of them solves *your* stack.

We believe the only durable answer is a **provider-agnostic framework**: a
canonical event algebra with per-provider adapters, one abstract decision
compiled into each platform's native controls, and degrade-safe semantics so
a supervisor failure composes with the live call as a no-op. Keep the stack
you have — or let Supafone manage all of it — and every capability here
(watcher, classification, QA, optimizer) works the same way. The formal
argument is in our paper,
[*The Sidecar Oracle*](https://labs.supafone.ai/research.html), and the
testing methodology in
[*Grading the Call*](https://labs.supafone.ai/research.html).

## Where this goes: self-healing agent swarms

The endgame isn't one agent on one number. It's **self-healing call centers**:
fleets of voice agents that test themselves before deploy (adversarial
auto-suites), watch themselves in production (the sidecar watcher), label
every finished call (post-call classification), and rewrite their own
standing directives from the evidence (the OPRO-style optimizer) — with
humans supervising distributions, not transcripts. Supafone Labs is built to
be the infrastructure layer for that: the event algebra, the supervision
channel, the grading system, and the improvement loop are the same primitives
a thousand-agent swarm needs. That's the product we are building toward, and
everything in these docs is a piece of it.

## Two ways to ship

Supafone Labs is the developer framework behind Supafone. It gives teams two
ways to ship production voice agents:

- **Agent Factory**: create complete phone, web, and campaign agents from code
  with managed stages, voices, numbers, tools, transcripts, recordings,
  widgets, usage, and Supafone Pro watcher attached. This path is designed to
  eliminate the need for customer-owned voice-platform, telephony, TTS, STT,
  and LLM keys before launch.
- **Self-healing Labs watcher**: keep Vapi, Retell, OpenAI Realtime, Grok,
  Ultravox, Gemini Live, ElevenLabs, Inworld, Deepgram, LiveKit, or another
  stack, then add the Supafone Labs second mind that listens off the hot path and
  sends silent corrective directives back to the live agent. Ten frameworks
  accept a live directive; **Bland does not** (closed live-call API — observe and
  score only), and Cartesia/Pipecat are n/a. See
  [Framework Support](framework-support.md).

There are two API surfaces:

| Surface | Base URL | Key | Primary use |
| --- | --- | --- | --- |
| Labs Cloud | `https://api.labs.supafone.ai` | `sl_live_...` | Oracle, TTS, STT, logs, builder, QA, optimizer |
| Hosted Agents | `https://api.supafone.ai/api/v1/labs` | `sl_live_...` (or scoped `sf_live_...`) | Hosted agent, number, voice, preset, and telephony provisioning |

**How many keys? One.** Since 0.4.4, your `sl_` Labs key authenticates on
**both** APIs ([one-key auth](api-keys-and-auth.md)): the Labs gateway
natively, and the product API — campaigns, dialing, agents, calls — via
`/v1/keys/introspect`, mapped to your app.supafone.ai account by owner email.
Both SDK constructors cross-fill every credential lane from a lone `sl_`
credential, and `SUPAFONE_TOKEN=sl_live_...` alone powers the MCP server end
to end. Everything data-plane — the oracle, TTS/STT, post-call analysis
(`postCallAnalysis` / `classify_call`), `qa.generate()`, QA history, logs,
telemetry — rides the same key. Scoped `sf_live_...` keys remain available
for hosted-agent-only deployments, and account login (email/password or JWT)
still works everywhere it did before.

Use the unscoped npm package:

```bash
npm i supafone-labs
```

Use the Python package:

```bash
pip install "supafone-labs[all]"
```

The default hosted-agent path is Supafone-managed. Developers do not need to
bring Twilio, Ultravox, Cartesia, Inworld, ElevenLabs, or Deepgram accounts just
to launch an agent. Real dedicated or premium phone-number purchases should be
explicit product choices, not implicit defaults.

BYOK is split into three separate lanes:

| BYOK lane | Examples |
| --- | --- |
| Agent/provider stack | Ultravox, Retell, Vapi, Bland, LiveKit, Pipecat, GPT Realtime, Grok |
| Telephony | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks |
| TTS | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS |

Teams can use any combination of managed and BYOK. For example, they can keep
Supafone-managed telephony but bring their own ElevenLabs key, or bring Telnyx
and Cartesia while still using the managed self-healing watcher.

Start with [Developer Workflows](developer-workflows.md) and
[Quickstart](quickstart.md), then read [API Keys and Auth](api-keys-and-auth.md).
For the full builder surface, read [Agent Factory](agent-factory.md),
[Call Stages](call-stages.md), [Voices and Previews](voices-and-previews.md),
and [Log Streaming](log-streaming.md). For how our QA stacks up against the
2026 field — and the enterprise roadmap it drives — read
[Testing Voice Agents (QA)](voice-qa-landscape.md).
