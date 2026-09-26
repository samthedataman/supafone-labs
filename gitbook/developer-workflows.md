# Developer Workflows

**Dashboard:** open [Supafone agents](https://app.supafone.ai/app/agents),
select your agent, and use its native realtime model controls. The older
[Labs workspace](https://labs.supafone.ai/builder.html) is the managed Ultravox
compatibility builder and links to these S2S controls.

Build a durable agent with Agent Factory, then choose its speech-to-speech
model through Supafone's S2S harness. The harness reuses the same prompt,
supported tools, fixed stages, and browser/carrier contracts when you switch
among supported models.

## Choose the speaking model

| Provider | Model | Default voice |
| --- | --- | --- |
| OpenAI | `gpt-realtime-2.1` | `marin` |
| OpenAI | `gpt-live-1` | `marin` |
| Google | `gemini-3.1-flash-live-preview` | `Puck` |
| xAI | `grok-voice-latest` | `eve` |

Every catalog model has browser and phone adapters for Supafone-managed phone,
BYO Twilio, BYO Telnyx, BYO Plivo, and BYO SIP. Discover the current choices
through `supafone.labs.capabilities()`; catalog support is distinct from your
workspace's credential and carrier readiness.

## Start with managed provider keys

Authenticate with your Supafone API key. The selected model uses a configured
Supafone platform key unless your account has supplied an encrypted BYOK key
for that provider. Read `GET /api/v1/labs/runtime?provider=openai` (or `google`,
`xai`) to check the source and status before calling. Customers do not need to
paste a provider key when the platform supplies one.

`source: platform` means a server credential exists. `source: account` means
an account key overrides it. `none` or `invalid` means setup is required.
Readiness does not prove that a key has model access; run a real preview after
selecting it. Keep model credentials separate from your Supafone application
key and from carrier credentials. See [Managed keys and BYOK](byok-providers.md).

## Create and preview

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN! });
const agent = await supafone.labs.agents.createInbound({
  agentKey: "northline-intake",
  name: "Northline intake",
  assistantName: "Maya",
  description: "Answer inquiries, capture the request, and book the next step.",
  realtime: { provider: "openai", model: "gpt-realtime-2.1", voice: "marin" },
  telephony: { mode: "supafone_managed", provider: "supafone" },
});
const preview = await supafone.labs.agents.testCall("northline-intake");
```

```python
import os
from supafone_labs import Supafone

supafone = Supafone(api_key=os.environ["SUPAFONE_TOKEN"])
agent = supafone.labs.agents.create_inbound({
    "agentKey": "northline-intake",
    "name": "Northline intake",
    "assistantName": "Maya",
    "description": "Answer inquiries, capture the request, and book the next step.",
    "realtime": {"provider": "openai", "model": "gpt-realtime-2.1", "voice": "marin"},
    "telephony": {"mode": "supafone_managed", "provider": "supafone"},
})
preview = supafone.labs.agents.test_call("northline-intake")
```

The returned browser session has a one-use ticket and sample rates. Use the
dashboard preview or a compatible audio client to speak to the agent;
`testCall` alone creates the session. No provider secret is returned.

## Switch an existing agent

```ts
await supafone.labs.agents.update("northline-intake", {
  realtime: { provider: "google", model: "gemini-3.1-flash-live-preview", voice: "Puck" },
});
```

```python
supafone.labs.agents.update("northline-intake", {
    "realtime": {"provider": "xai", "model": "grok-voice-latest", "voice": "eve"},
})
```

A model change takes effect on a new session. Keep your supported native
workflow, then compare model behavior using the same tasks and tools. Select
a voice valid for the new model. This is configuration reuse, not a promise of
identical speech, timing, tool decisions, or seamless mid-call model handoff.

## Move from browser to phone

Keep the `realtime` selection and configure the phone lane. Supafone-managed
phone uses approved managed infrastructure; BYO Twilio, Telnyx, Plivo, and SIP
use their own account credentials and routing. Browser success does not prove
carrier readiness. Test caller ID, webhook signatures, inbound routing, and
outbound behavior for the selected carrier. Follow the
[native carrier guide](realtime-agent-factory.md#phone-calls-and-carrier-selection).

## Understand the native feature boundary

Native agents use fixed intake → booking → confirmation stages and allowed
knowledge, lead capture, scheduling, SMS/email, and custom tools. Supafone runs
the tools server-side with agent and account authority.

The native transport currently has no recording, Supervisor coaching, human
transfer, specialist-team handoff, DTMF navigation, public widget, or live language/voice profile
switching. The large managed TTS catalog does not replace native model voices.
Use the [native guide](realtime-agent-factory.md#feature-boundaries) as the
feature contract.

## Use the broader hosted feature set

Omitting `realtime` keeps the managed Ultravox compatibility runtime. This is
the path for the full hosted planner, compatible TTS voices, recording,
Supervisor attachment, transfer, widgets, and opt-in
[live language/voice routing](live-language-voice-routing.md).
These capabilities should not be inferred from native S2S model support.

[Agent Factory](agent-factory.md), [custom tools](custom-tools.md), and
[campaigns as code](outbound-call-campaigns.md) describe their own setup and
runtime boundaries.

## Supervise an existing agent

Supafone Supervisor is a separate offering for a supported agent you already
run. It observes events and proposes bounded guidance; delivery capability
varies by adapter.

```python
import supafone_labs

brain = supafone_labs.supercharge(my_agent)
result = await brain.observe(raw_platform_event)
```

Check [framework coverage](framework-support.md) and
[programmable directives](programmable-supervisor-directives.md). The presence
of a Supervisor adapter for a provider does not mean Supervisor is enabled in
that provider's native Agent Factory transport.

## Key Routing

| Work | Key | Base URL |
| --- | --- | --- |
| Agent Factory, model readiness, numbers, hosted voices | `sl_live_...` or scoped `sf_live_...` | `https://api.supafone.ai/api/v1/labs` |
| Supervisor, TTS previews, STT, usage, logs, QA | `sl_live_...` | `https://api.labs.supafone.ai` |
| Campaigns, dialing, calls | `sl_live_...` or account JWT | `https://api.supafone.ai` |

One linked `sl_` key can authenticate both APIs. See [API keys and auth](api-keys-and-auth.md).
Exports should contain the selected `realtime` provider/model/voice and phone
configuration, never resolved provider secrets.
