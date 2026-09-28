# Developer Workflows

## One superclass, five providers

Import `SupafoneS2S` and its provider classes: `UltravoxS2S`, `OpenAIS2S`,
`GeminiS2S`, `GrokS2S`, and `HydraS2S`. Each offers `create`, `apply`, and
`testCall` (Python `test_call`) through the same hosted agent contract.
`apply` changes the next call on the existing agent; preview always uses the
saved configuration. [See complete Python and TypeScript examples](unified-s2s.md).


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
| Smallest AI | `hydra-v1.0` | `sterling` |
| Smallest AI | `hydra-v1.1` | `maya` |

Every catalog model has browser and phone adapters for Supafone-managed phone,
BYO Twilio, BYO Telnyx, BYO Plivo, and BYO SIP. Discover the current choices
through `supafone.labs.capabilities()`; catalog support is distinct from your
workspace's credential and carrier readiness.

## Start with managed provider keys

Authenticate with your Supafone API key. The selected model uses a configured
Supafone platform key unless your account has supplied an encrypted BYOK key
for that provider. Read `GET /api/v1/labs/runtime?provider=openai` (or `google`,
`xai`, `smallest`) to check the source and status before calling. Customers do not need to
paste a provider key when the platform supplies one.

`source: platform` means a server credential exists. `source: account` means
an account key overrides it. `none` or `invalid` means setup is required.
Readiness does not prove that a key has model access; run a real preview after
selecting it. Keep model credentials separate from your Supafone application
key and from carrier credentials. See [Managed keys and BYOK](byok-providers.md).

## Create and preview

```ts
import { Supafone, HydraS2S } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN! });
const engine = new HydraS2S(supafone, { model: "hydra-v1.1", voice: "maya" });
const agent = await engine.create({
  agentKey: "northline-intake",
  name: "Northline intake",
  description: "Answer inquiries, capture the request, and book the next step.",
  telephony: { mode: "supafone_managed", provider: "supafone" },
});
const preview = await engine.testCall("northline-intake");
```

```python
import os
from supafone_labs import Supafone, HydraS2S

supafone = Supafone(api_key=os.environ["SUPAFONE_TOKEN"])
engine = HydraS2S(supafone, model="hydra-v1.1", voice="maya")
agent = engine.create(
    agentKey="northline-intake",
    name="Northline intake",
    description="Answer inquiries, capture the request, and book the next step.",
    telephony={"mode": "supafone_managed", "provider": "supafone"},
)
preview = engine.test_call("northline-intake")
```

The returned browser session has a one-use ticket and sample rates. Use the
dashboard preview or a compatible audio client to speak to the agent;
`testCall` alone creates the session. No provider secret is returned.

## Switch an existing agent

```ts
import { OpenAIS2S } from "supafone-labs";

const next = new OpenAIS2S(supafone, { model: "gpt-realtime-2.1", voice: "marin" });
await next.apply("northline-intake");
const preview = await next.testCall("northline-intake");
```

```python
from supafone_labs import OpenAIS2S

next_engine = OpenAIS2S(supafone, model="gpt-realtime-2.1", voice="marin")
next_engine.apply("northline-intake")
preview = next_engine.test_call("northline-intake")
```

Use the same methods with `GeminiS2S`, `GrokS2S`, or `HydraS2S`. Applying
`UltravoxS2S` returns to the managed default. **Preview uses the saved agent;
call `apply` before testing a new selection.**

A model change takes effect on a new session and keeps the agent's phone
assignment. Native-to-native switches preserve supported tools and fixed
stages. Entering native S2S from the Ultravox planner uses the fixed native
stage contract; returning to Ultravox does not restore an older arbitrary
stage plan. Select a voice valid for the new model and compare behavior with
the same tasks. Speech, timing, and tool decisions can differ by provider.

## Move from browser to phone

Keep the `realtime` selection and configure the phone lane. Supafone-managed
phone uses approved managed infrastructure; BYO Twilio, Telnyx, Plivo, and SIP
use their own account credentials and routing. Browser success does not prove
carrier readiness. Test caller ID, webhook signatures, inbound routing, and
outbound behavior for the selected carrier. Follow the
[native carrier guide](realtime-agent-factory.md#phone-calls-and-carrier-selection).

## Enable coaching for any speaking model

Set `supervisor: true` or a managed/BYOK Supervisor configuration on the agent.
All five hosted speaking families support coaching. Native OpenAI, Gemini,
Grok, and Hydra request guidance through `check_guidance`; Hydra supplies
model-reported context because it does not emit transcripts. The Supervisor
model needs its own configured credentials. An enabled setting is not proof
of a running coach. See [hosted coaching](realtime-agent-factory.md#supervisor-coaching-across-all-five-speaking-families).

## Understand the native feature boundary

Native agents use fixed intake → booking → confirmation stages and allowed
knowledge, lead capture, scheduling, SMS/email, and custom tools. Supafone runs
the tools server-side with agent and account authority.

The native transport currently has no recording, human
transfer, specialist-team handoff, DTMF navigation, public widget, or live language/voice profile
switching. Hydra has no native transcript stream and cannot change persona or voice
mid-session. Its fixed stages advance through validated tool results. The
large managed TTS catalog does not replace native model voices.
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
of a Supervisor adapter for a provider is separate from hosted Agent Factory
support. All five hosted speaking families support coaching; an individual
agent must also have supervision enabled and a configured Supervisor model.

## Key Routing

| Work | Key | Base URL |
| --- | --- | --- |
| Agent Factory, model readiness, numbers, hosted voices | `sl_live_...` or scoped `sf_live_...` | `https://api.supafone.ai/api/v1/labs` |
| Supervisor, TTS previews, STT, usage, logs, QA | `sl_live_...` | `https://api.labs.supafone.ai` |
| Campaigns, dialing, calls | `sl_live_...` or account JWT | `https://api.supafone.ai` |

One linked `sl_` key can authenticate both APIs. See [API keys and auth](api-keys-and-auth.md).
Exports should contain the selected `realtime` provider/model/voice and phone
configuration, never resolved provider secrets.
