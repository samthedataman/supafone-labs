# Shared S2S Interface

Use one `SupafoneS2S` interface to create and switch a Supafone voice agent
across **Ultravox, OpenAI, Gemini, Grok, and Smallest AI Hydra**. The exported
provider classes share the same creation, selection, and preview methods in
Python and TypeScript. Your application keeps the same Supafone agent and
phone number when it changes the speaking provider.

The SDK selects and configures a hosted runtime. It does not put vendor keys
in a browser or start a provider connection on its own. The server owns audio,
allowed tools, stages, and credential resolution.

## Two voice-output choices in one Agent Factory

**Ultravox + custom TTS** keeps the existing managed phone agent and lets a
compatible Cartesia, ElevenLabs, Inworld, or Ultravox catalog voice supply its
speech. **Native S2S** selects OpenAI, Gemini, Grok, or Hydra and uses that
model's own voice list. Both are available through `SupafoneS2S`; external TTS
is not a universal voice override for native models.

[Compare both paths and create an Ultravox agent with custom TTS](voice-output-modes.md).

## Provider classes

| Exported class | Provider ID | Model choices | Runtime behavior |
| --- | --- | --- | --- |
| `UltravoxS2S` | `ultravox` | Existing managed Ultravox configuration | Default managed runtime; keeps its existing voice configuration |
| `OpenAIS2S` | `openai` | `gpt-realtime-2.1`, `gpt-live-1` | Native realtime; GPT Live also uses delegated reasoning |
| `GeminiS2S` | `google` | `gemini-3.1-flash-live-preview` | Native realtime; preview model |
| `GrokS2S` | `xai` | `grok-voice-latest` | Native realtime |
| `HydraS2S` | `smallest` | `hydra-v1.0`, `hydra-v1.1` | Native realtime; no native transcripts; persona and voice fixed per session |

All five classes extend the exported `SupafoneS2S` base class. This is **five
speaking-provider families**, with **six native model choices plus the Ultravox
default**. It is a supported catalog, not a claim to include every S2S model.

## Create an agent with Hydra

TypeScript:

```ts
import { Supafone, HydraS2S } from "supafone-labs";

const client = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN! });
const engine = new HydraS2S(client, { model: "hydra-v1.1", voice: "maya" });

const agent = await engine.create({
  agentKey: "northline-intake",
  name: "Northline intake",
  description: "Understand the request and book the right next step.",
});
const preview = await engine.testCall("northline-intake");
console.log(preview.browser_session);
```

Python:

```python
import os
from supafone_labs import Supafone, HydraS2S

client = Supafone(api_key=os.environ["SUPAFONE_TOKEN"])
engine = HydraS2S(client, model="hydra-v1.1", voice="maya")
agent = engine.create(
    agentKey="northline-intake",
    name="Northline intake",
    description="Understand the request and book the right next step.",
)
preview = engine.test_call("northline-intake")
print(preview["browser_session"])
```

Create the provider credential on the Supafone server before a live preview.
For Hydra, that is the managed `SMALLEST_API_KEY` or an encrypted account
BYOK override. Your application only needs its Supafone key when a platform
credential is configured. Missing configuration is reported as setup required.
Creating the agent is separate from connecting audio or making a phone call.

## Switch the same fone

Choose a new provider object and explicitly apply it to the existing agent:

```ts
import { SupafoneS2S, OpenAIS2S, GeminiS2S, GrokS2S, UltravoxS2S } from "supafone-labs";

const next: SupafoneS2S = new OpenAIS2S(client, {
  model: "gpt-realtime-2.1", voice: "marin",
});
await next.apply("northline-intake");
const preview = await next.testCall("northline-intake");

// The same operation selects another supported family:
await new GeminiS2S(client).apply("northline-intake");
await new GrokS2S(client).apply("northline-intake");

// Return to the default managed Ultravox runtime:
await new UltravoxS2S(client).apply("northline-intake");
```

```python
from supafone_labs import SupafoneS2S, OpenAIS2S, GeminiS2S, GrokS2S, UltravoxS2S

next_engine: SupafoneS2S = OpenAIS2S(client, model="gpt-realtime-2.1", voice="marin")
next_engine.apply("northline-intake")
preview = next_engine.test_call("northline-intake")

GeminiS2S(client).apply("northline-intake")
GrokS2S(client).apply("northline-intake")
UltravoxS2S(client).apply("northline-intake")
```

Each `apply` updates the saved agent's speaking selection for its **next
session**. It does not move an active call between providers or buy another
number. Existing phone assignment and tools stay on the agent; only tools
supported by the selected runtime are available during that call. Check the
new provider's credentials, then preview before using it with callers.

Moving from the broader Ultravox planner to native S2S uses the supported
intake → booking → confirmation stage contract. Native-to-native switches
retain those stages and their instructions. Returning to Ultravox does not
restore an earlier arbitrary stage plan automatically.

## Method contract

| Operation | TypeScript | Python | Meaning |
| --- | --- | --- | --- |
| Create agent | `engine.create({...})` | `engine.create(name="...", ...)` | Create through Agent Factory using this provider selection |
| Select for an existing agent | `engine.apply(agentKey)` | `engine.apply(agent_key)` | Update only the speaking selection for the next session |
| Preview the saved agent | `engine.testCall(agentKey)` | `engine.test_call(agent_key)` | Return a session for the agent's currently saved configuration |
| Inspect selection | `engine.realtime` | `engine.realtime` | Native provider/model/voice selection; `null`/`None` for Ultravox |

**Preview does not apply the object's selection.** Call `apply` first when
switching providers. An `OpenAIS2S` object's preview method will still preview
the saved Hydra agent if you never applied the OpenAI selection.

Native classes may omit model and voice to use catalog defaults. Ultravox does
not accept native model/voice constructor options: configure its voice through
the existing managed-agent settings. Use the base class directly when provider
choice comes from validated application configuration:

```ts
const engine = new SupafoneS2S(client, {
  provider: "smallest", model: "hydra-v1.1", voice: "maya",
});
```

```python
engine = SupafoneS2S(client, provider="smallest", model="hydra-v1.1", voice="maya")
```

Plain REST and existing SDK calls remain available. Native `apply` corresponds
to `PATCH /api/v1/labs/agents/{agent_key}` with a `realtime` selection;
Ultravox applies `realtime: null`. No `client.s2s` namespace is required.

## Shared transport, explicit capabilities

The native choices use authenticated browser audio or Supafone-managed phone,
BYO Twilio, BYO Telnyx, BYO Plivo, and BYO SIP. Phone provider configuration is
account-scoped and separate from the speaking selection. A model switch does
not configure a carrier, change caller ID, or establish an inbound route.

Ultravox browser sessions use its managed transport. Native choices use
`supafone_realtime`. Audio clients must follow the returned transport and
sample rates instead of guessing from the provider name.

Hydra currently supports English only. It has no native transcript stream; its persona and voice are fixed for
the connection. Supafone advances its fixed stages through validated tool
results, not a persona rewrite. Native recording, Supervisor coaching, human
transfer, specialist-team handoff, DTMF, public widgets, and live language/voice
profile switching remain unavailable. Ultravox retains its broader compatible
hosted features. See the [native model matrix and limits](realtime-agent-factory.md).

A key's presence is not proof of model permissions or successful calls. Check
runtime status and validate browser and carrier behavior in the actual
deployment. [Managed credentials and BYOK](byok-providers.md) explain who
supplies the selected provider's key.
