# Product Overview

Supafone Labs gives developers a shared **speech-to-speech (S2S) harness** and
an **Agent Factory**. The harness connects the speaking model to the agent's
prompt, allowed tools, stages, credentials, and audio transport. Agent Factory
creates and manages the agent configuration used by that harness.

## Shared S2S interface

Use the same `SupafoneS2S` interface for **Ultravox, OpenAI, Gemini, Grok,
and Smallest AI Hydra**. Provider subclasses supply the selection while Agent
Factory keeps the agent and phone identity. Ultravox stays the default; the
native catalog offers six model choices. See [the common interface](unified-s2s.md)
for the class contract and switching examples.

Model changes apply to new calls, not a live-call handoff. Capabilities remain
provider-specific: Hydra has no native transcripts and cannot change its
persona or voice mid-session. Check credentials and test the selected provider
before a customer call.

## Two voice-output choices in one Agent Factory

**Ultravox + custom TTS** keeps the existing managed phone agent and lets a
compatible Cartesia, ElevenLabs, Inworld, or Ultravox catalog voice supply its
speech. **Native S2S** selects OpenAI, Gemini, Grok, or Hydra and uses that
model's own voice list. Both are available through `SupafoneS2S`; external TTS
is not a universal voice override for native models.

[Compare both paths and create an Ultravox agent with custom TTS](voice-output-modes.md).

## Build once, choose the model

Create an agent with a `realtime: { provider, model, voice }` selection. The
native catalog includes OpenAI `gpt-realtime-2.1`, OpenAI `gpt-live-1`, Google
`gemini-3.1-flash-live-preview`, xAI `grok-voice-latest`, and Smallest AI
`hydra-v1.0` and `hydra-v1.1`. Use the shared provider classes or the underlying
`realtime` selection; `UltravoxS2S` keeps the existing managed default.

The same agent can use authenticated browser previews, Supafone-managed phone,
BYO Twilio, BYO Telnyx, BYO Plivo, or BYO SIP. Update the selection before a new
session to compare another model. Your agent identity, instructions, supported
tools, fixed intake → booking → confirmation stages, and carrier configuration
stay together; choose a model-compatible voice with each switch.

## Managed keys first

Your Supafone key authenticates your application. Supafone then resolves the
selected speaking model's credential on the server: an encrypted account BYOK
key, if supplied, otherwise a configured platform key. A platform key means
customers can use the model without creating their own provider account.

Read the selected provider's runtime status before launch. Missing credentials
are reported as setup required. A catalog entry and a configured credential do
not establish model entitlement or successful live calls. Carrier readiness is
checked separately from model readiness.

## Three product surfaces

| Surface | Purpose | Runtime boundary |
| --- | --- | --- |
| Native realtime Agent Factory | Build and switch S2S agents through the hosted API and dashboard | Six native catalog models, fixed native stages, supported server tools, browser and phone |
| Managed compatibility Agent Factory | Continue existing Ultravox-backed hosted workflows | Selected when `realtime` is omitted; includes the broader planner and compatible recording, transfer, widgets, and supervision features |
| Supafone Supervisor | Observe and coach agents you already run | Separate SDK/runtime with provider-specific guidance and observation capabilities |

Supafone Supervisor is an independent reasoning layer available on all five
Agent Factory speaking families, as well as supported external stacks. Native
models receive guidance through the `check_guidance` tool. Hydra provides
model-reported context rather than transcripts. See the
[framework matrix](framework-support.md) for delivery differences.

## API and SDK surfaces

Use Python, TypeScript, REST, or the dashboard with the same hosted agent
contract. Hosted agents and model readiness live at
`https://api.supafone.ai/api/v1/labs`; Labs Cloud supervision, QA, TTS/STT,
usage, and logs live at `https://api.labs.supafone.ai`. One `sl_live_...` key
can authenticate both APIs with the linked account; scoped `sf_live_...` keys
remain available for hosted-agent-only integrations.

[Start the quickstart](quickstart.md), read the
[native runtime limits](realtime-agent-factory.md#feature-boundaries), or see
[Agent Factory](agent-factory.md) for a complete creation workflow.
