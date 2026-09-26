# Product Overview

Supafone Labs gives developers a shared **speech-to-speech (S2S) harness** and
an **Agent Factory**. The harness connects the speaking model to the agent's
prompt, allowed tools, stages, credentials, and audio transport. Agent Factory
creates and manages the agent configuration used by that harness.

## Build once, choose the model

Create an agent with a `realtime: { provider, model, voice }` selection. The
native catalog includes OpenAI `gpt-realtime-2.1`, OpenAI `gpt-live-1`, Google
`gemini-3.1-flash-live-preview`, and xAI `grok-voice-latest`.

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
| Native realtime Agent Factory | Build and switch S2S agents through the hosted API and dashboard | Four catalog models, fixed native stages, supported server tools, browser and phone |
| Managed compatibility Agent Factory | Continue existing Ultravox-backed hosted workflows | Selected when `realtime` is omitted; includes the broader planner and compatible recording, transfer, widgets, and supervision features |
| Supafone Supervisor | Observe and coach agents you already run | Separate SDK/runtime with provider-specific guidance and observation capabilities |

Supafone Supervisor is an independent product surface. It is not currently
attached to the native S2S transport. The managed compatibility path and
supported external stacks can use it as documented in the
[framework matrix](framework-support.md).

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
