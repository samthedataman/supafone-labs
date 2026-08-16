# Product Overview

Supafone Labs is built around a simple architecture: the live voice agent keeps
talking inside the realtime latency budget, while Supafone Labs runs a second
mind beside the call. That second mind reads transcripts, audio-derived state,
tool outcomes, and account context, then returns a silent directive only when it
can improve the call.

## Product Surfaces

**Voice Watcher is the defining product surface.** It is the model-agnostic
supervisor contract that observes empathy and operational patterns across
turns, verifies tool truth and workflow progress, and emits a silent native
directive only when intervention is useful.

**Labs Cloud** is hosted at `https://api.labs.supafone.ai` with an `sl_live_...`
key. This path runs the oracle, hosted TTS/STT, live multilingual
transcription, logs, usage, QA, optimizer, and the managed side of Voice
Watcher.

**Open-source SDK runtime** lives in the Python package `supafone-labs` and can
supervise an existing stack. It includes the canonical call-state contract,
deterministic runtime policies, provider adapters, replay, telemetry, and
local or hosted supervisor-model modes.

**Hosted Supafone agents** are created through the Supafone hosted-agent API at
`https://api.supafone.ai/api/v1/labs` with your `sl_live_...` key (one-key
auth) or a scoped `sf_live_...` key. This path is
for complete agents: inbound receptionists, outbound sales agents, web agents,
campaign agents, generated executable call plans, managed numbers, presets,
tools, artifacts, and Supafone Pro.
This is the Agent Factory path: by default, Supafone supplies the operational
provider layer so the developer does not need to bring voice-platform,
telephony, TTS, STT, or LLM keys to get started. This Agent Factory path is a
secondary delivery convenience; the supervisor also works when Supafone did
not create the agent.

## Core Concepts

- **Self-healing watcher**: the Supafone Labs second mind that supervises a
  hosted or BYOK agent and emits silent corrections.
- **Empathy pattern state**: cross-turn intent, urgency, emotion, language,
  trust, progress, and tool truth used to decide whether a nudge is warranted.
- **Runtime**: canonical call events, state, policies, and provider adapters.
- **Oracle**: hosted or BYO LLM layer that decides whether to whisper.
- **Whisper**: a silent directive injected into the agent's native control
  channel. The caller never hears it.
- **Watcher**: Supafone Pro live supervision attached to a hosted or BYO agent.
- **Standing directive**: a persistent coaching preamble improved from
  post-call outcomes.
- **Agent Factory**: the secondary hosted-agent creation path that turns one
  job description into validated prompts and a 3–8 stage runtime, then adds
  managed platform, telephony, TTS/STT/LLM, numbers, tools, and logs.
- **Number strategy**: shared pool by default, dedicated/premium only by
  explicit choice.

## Supported Build Paths

| Path | Best for | Package/API |
| --- | --- | --- |
| Hosted inbound agent | Intake, reception, support | `supafone.labs.agents.createInboundWithNumber()` |
| Hosted outbound agent | Sales, speed-to-lead, campaigns | `supafone.labs.agents.createOutboundWithNumber()` |
| Web agent | Website widget and web intake | `POST /api/v1/labs/agents` |
| Bring your stack | Teams already on a voice platform | Python `supafone_labs.supercharge()` |
| Local runtime | Testing adapters and policies offline | Python runtime modules |

## Production Defaults

- Hosted agents default to Supafone-managed provider accounts.
- BYOK is optional and split into independent agent-runtime, telephony, TTS,
  STT, and supervisor-model lanes. The audited providers and exact support
  depth are maintained in the [framework coverage matrix](framework-support.md).
- Labs Cloud requests are billed against a minute balance.
- The watcher is timeout-bounded and degrade-safe: if it cannot produce a useful
  directive quickly, it stays silent.
- Real phone-number purchases, dedicated number reservations, and premium
  numbers are never assumed. They should be explicit user/admin actions.
