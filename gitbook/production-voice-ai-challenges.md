# Production Voice AI: Daily Problems Supafone Solves

A voice agent demo usually proves that a model can talk. Production asks harder
questions: can the call change language without restarting, keep the correct
voice and workflow state, survive a worker handoff, verify tools, fail over
safely, and remain observable across providers?

Supafone treats those as control-plane problems. The realtime agent stays on
the low-latency speaking path. Voice Watcher and the shared runtime handle
supervision, continuity, policy, telemetry, and recovery beside the call.

The core product is the model-agnostic supervisor, not the hosted Agent
Factory. Its first-principles advantage is pattern memory: it treats empathy as
evidence-backed changes in intent, urgency, emotion, language, trust, workflow
progress, and tool truth across turns. Agent Factory is the secondary path for
teams that also want Supafone to provision the speaking agent and surrounding
infrastructure.

## The day-to-day challenge map

| What developers fight every day | Supafone's answer | Practical benefit |
| --- | --- | --- |
| A caller changes language mid-call | Up to four approved language profiles, explicit-request priority, evidence-gated automatic detection, and two-way switching | The caller does not hang up, restart intake, or repeat facts |
| One voice sounds wrong in another language | A dedicated voice and regional hint per language, with native/external voice resolution and graceful fallback | Better pronunciation without turning voice loading into a call-ending dependency |
| Switching language resets the agent | The same call, persona, prompt, tools, workflow stage, captured facts, and runtime settings remain active | Booking, intake, transfer, signing, CRM, and campaign work continue in context |
| Every voice vendor exposes different controls | One canonical Watcher event/directive contract compiled through provider adapters | Teams can change voice stacks without rebuilding supervision and QA |
| Tool calls fail but the agent claims success | Voice Watcher compares spoken claims with tool results and can inject a silent correction | Fewer false booking, sending, pricing, and policy confirmations |
| A supervisor is needed, but another agent would add latency | SecondMind reasons off the audio hot path and privately guides the speaking agent | Live coaching without making every caller wait for the slower model |
| Multiple workers lose live-call state | Durable language, voice, stage, and telemetry continuity across workers | Scaling application workers does not break routing or handoffs |
| Automatic language routing becomes unsafe guesswork | Explicit requests take priority; inference requires a clear utterance, a cooldown, configured-language enforcement, and tenant/call validation | No routing based only on accent, name, nationality, or presumed identity |
| A provider or coaching feature fails mid-call | Timeout-bounded, degrade-safe behavior and voice fallback | The underlying customer call continues instead of crashing |
| Inbound, outbound, browser, and campaign agents drift apart | The same routing overlay and tool-preservation contract span standard inbound, normal outbound, Warm Campaign, staged, and mono-agent paths | One behavior model instead of four separate implementations |
| Post-call data cannot explain what happened | Bounded language paths, starting/final voice, evidence, confidence, and fallback telemetry | Teams can debug switches and improve agents without unbounded transcript-like state |
| A popular line exceeds AI capacity | Optional concurrency controls plus overflow to another AI agent, PSTN number, or SIP destination | Calls can fail over without reassigning the original number |

## Multilingual calls without a reset

Each agent can define as many as four approved language profiles. A profile can
carry a regional tag such as `es-PR`, `en-US`, `hi-IN`, or `vi-VN` and its own
voice. The primary profile controls the greeting; callers can then request a
different configured language during the same session.

An explicit request such as “Can we speak Spanish?” can route immediately.
Automatic detection requires a sufficiently clear, complete utterance and is
cooldown-protected. The caller can later switch back. Disabling Voice Routing
keeps the existing single-language behavior for legacy agents.

During a switch Supafone preserves:

- the live PSTN or WebRTC session,
- agent identity and safety prompt,
- booking, transfer, intake, form, CRM, signing, callback, and campaign tools,
- the current workflow stage,
- names, numbers, eligibility answers, matter facts, and prior tool results,
- model temperature and other runtime behavior.

If a requested external voice cannot load, the language can still change while
the current voice remains active. A voice-provider failure is not allowed to
terminate the call.

## One Watcher across frameworks and carriers

Voice Watcher normalizes live events from the selected voice framework, reasons
over one contract, and compiles a safe directive back into that framework's
supported control channel. See [Framework Support](framework-support.md) for
the exact injection primitive and caveats for each stack.

Telephony is a separate account-level choice. Hosted agents can use managed
telephony where approved or the customer's configured Twilio, Telnyx, Plivo,
or SIP credentials. Provider secrets remain server-side.

The MCP does not need a Telnyx-specific calling tool. `start_call_and_watch`
starts the selected account-owned agent; the private runtime uses that agent's
configured carrier. With a Telnyx-backed agent, the same MCP call therefore
uses Telnyx and returns the same authenticated watch link—without exposing a
Telnyx API key to the model or the link.

```text
Claude / Cursor / another MCP client
  -> Supafone MCP: start_call_and_watch(confirmRealCall=true)
  -> account-owned agent and outbound-policy checks
  -> configured carrier: Telnyx, Twilio, Plivo, or SIP
  -> secret-free authenticated dashboard link
```

## Safety and reliability are part of the contract

The runtime rejects unsupported routes and mismatched agency/call context.
Server-controlled identifiers bind internal tools to the active tenant and
call. Inference-driven language changes have a cooldown, and the system cannot
invent an unconfigured language.

Live state is stored outside one web worker, so a call remains coherent when a
later runtime event reaches a different worker than the one that created it.
Voice routing, Voice Watcher, and SecondMind are isolated from the underlying
call: a timeout or provider error yields no intervention rather than a dropped
caller.

The operator UI only reports coaching as `LIVE` after the backend coach has
actually started. It can display caller turns, Watcher reads, and delivered
guidance while preserving tenant isolation.

## What developers get

- One SDK flag to provision hosted agents with Voice Watcher enabled.
- One event/directive model for existing Vapi, Retell, Ultravox, OpenAI
  Realtime, LiveKit, Pipecat, Deepgram, ElevenLabs, and compatible stacks.
- One MCP action that can launch an approved real call and return the exact
  authenticated live-call dashboard.
- One continuity model for multilingual inbound, outbound, browser, staged,
  and Warm Campaign calls.
- One bounded telemetry model for QA, PI/medical follow-up metadata, and voice
  fallback monitoring.
- One capacity model for AI overflow, PSTN/SIP fallback, timers, announcements,
  and original-number protection.

## Current proof boundary

The implementation and safety contracts above are covered by runtime and UI
tests. The remaining release proof is a controlled live call that demonstrates
the audible provider voice change on both PSTN and WebRTC. Accent
classification is not a feature, and full switching parity for specialized
Stanley/admin sales runtimes is not advertised yet.

Next: [enable Voice Watcher](self-healing-watcher.md), review
[framework support](framework-support.md), or configure the
[MCP server](mcp-server.md).
