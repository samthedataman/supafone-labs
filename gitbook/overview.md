# Product Overview

Supafone is an **S2S routing hub with Supervisor**. Choose the model that talks
to callers, then use a separate reasoning model to observe the call and guide
it. One API connects **Ultravox, OpenAI, Gemini, Grok and Smallest AI Hydra**.

Agent Factory saves your agent's instructions, tools and call stages. Switching
the speaking model keeps that setup together. You choose the saved model;
Supafone connects the call to it.

## Choose how to connect

| Option | What you supply |
| --- | --- |
| **One Supafone API key** | Your account key; Supafone supplies the configured speaking and Supervisor credentials |
| **Bring your own keys** | A speaking-provider key, a Supervisor reasoning key, or both |

Speaking and Supervisor choices are independent. For example, use your OpenAI
key for speech and your Anthropic key for Supervisor, or use Supafone's managed
Supervisor with your own speaking key.

[Create a supervised agent](quickstart.md) · [Connect your own keys](byok-providers.md)

## Shared S2S interface

Use the same `SupafoneS2S` interface for **Ultravox, OpenAI, Gemini, Grok,
and Smallest AI Hydra**. Provider subclasses supply the selection while Agent
Factory keeps the agent and phone identity. Ultravox stays the default; the
native catalog offers six model choices. See [the common interface](unified-s2s.md)
for the class contract and switching examples.

Ordinary model updates apply to new calls; native live handoff requires a
separate opt-in runtime policy. Capabilities remain
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
tools, custom stage plan, and carrier configuration
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
| Native realtime Agent Factory | Build and switch S2S agents through the hosted API and dashboard | Six native catalog models, shared custom stages, supported server tools, browser and phone |
| Managed compatibility Agent Factory | Continue existing Ultravox-backed hosted workflows | Selected when `realtime` is omitted; shares the planner and workflow; retains compatible external TTS and live language/voice profiles |
| Supafone Supervisor | Observe the call and guide the speaking agent | Hosted agents use the `supervisor` setting; external stacks use a separate adapter |

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
