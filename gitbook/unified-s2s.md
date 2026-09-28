# Shared S2S Interface

Use one `SupafoneS2S` interface to create and switch a Supafone voice agent
across **Ultravox, OpenAI, Gemini, Grok, and Smallest AI Hydra**. The exported
provider classes share the same creation, selection, and preview methods in
Python and TypeScript. Your application keeps the same Supafone agent and
phone number when it changes the speaking provider.

The SDK selects and configures a hosted runtime. It does not put vendor keys
in a browser or start a provider connection on its own. The server owns audio,
allowed tools, stages, and credential resolution.

## Create a supervised S2S agent

**Hosted requirements:** the selected speaking model and Supervisor need
configured credentials. Native models use the shared call relay and guidance
tools. See [SDK installation and readiness](https://labs.supafone.ai/docs/sdk-installation/)
before testing a provider.

Pass `supervisor` to **`create` on the base class**. The constructor selects the
speaking provider, model and voice; `create` configures the hosted agent,
including its Supervisor. You do not need a separate Supervisor client or
standalone adapter for a hosted S2S agent.

TypeScript:

```ts
import { Supafone, SupafoneS2S } from "supafone-labs";

const client = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN! });
const engine = new SupafoneS2S(client, {
  provider: "smallest", model: "hydra-v1.1", voice: "maya",
});

const agent = await engine.create({
  agentKey: "northline-intake",
  name: "Northline intake",
  description: "Understand the request and book the right next step.",
  supervisor: true,
});
```

Python:

```python
import os
from supafone_labs import Supafone, SupafoneS2S

client = Supafone(api_key=os.environ["SUPAFONE_TOKEN"])
engine = SupafoneS2S(client, provider="smallest", model="hydra-v1.1", voice="maya")
agent = engine.create(
    agent_key="northline-intake",
    name="Northline intake",
    description="Understand the request and book the right next step.",
    supervisor=True,
)
```

`supervisor=True` / `true` explicitly enables hosted coaching. A new `Supafone`
client already defaults to enabled supervision when you omit this field; if
you configure a different client default, an explicit create setting overrides
it. To explicitly choose Supafone's managed Supervisor credentials, use
`supervisor={"enabled": True, "mode": "managed"}` in Python or
`supervisor: { enabled: true, mode: "managed" }` in TypeScript. Speaking-provider
credentials and Supervisor credentials are separate.

The same create setting works with `UltravoxS2S`, `OpenAIS2S`, `GeminiS2S`,
`GrokS2S` and `HydraS2S`. The hosted deployment must support the selected runtime
and have its provider and Supervisor credentials configured. For Hydra, the
speaking credential is `SMALLEST_API_KEY` or an encrypted account BYOK override.
Creating an agent does not connect audio or place a call. Start a preview with
`engine.test_call("northline-intake")` / `engine.testCall("northline-intake")`
after checking readiness.

## Choose platform keys or your own speaking key

All five speaking families use account runtime credentials. A saved account
key takes priority; otherwise Supafone's configured platform key is used.
Keep provider keys out of the `SupafoneS2S` constructor and `realtime`.

```python
client.labs.runtime.configure(
    provider="openai", mode="byok",
    credentials={"api_key": os.environ["OPENAI_API_KEY"]},
)
status = client.labs.runtime.get(provider="openai")
# Account-wide reset to the platform default for future OpenAI calls.
client.labs.runtime.configure(provider="openai", mode="supafone_managed")
```

```ts
await client.labs.runtime.configure({
  provider: "openai", mode: "byok", credentials: { apiKey: process.env.OPENAI_API_KEY! },
});
const status = await client.labs.runtime.get({ provider: "openai" });
await client.labs.runtime.configure({ provider: "openai", mode: "supafone_managed" });
```

These updates require account-admin permission and affect future calls for all
agents using that provider. They do not change Supervisor's reasoning key.
Explicit reset and updated readiness controls require **0.7.2** and the pending
backend rollout. [All five provider keys and CLI setup](https://labs.supafone.ai/docs/byok-providers/)
explains the provider IDs, credential precedence and readiness.

## Enable or disable Supervisor on an existing agent

Update the saved agent through the same client:

```ts
await client.labs.agents.update("northline-intake", {
  supervisor: { enabled: true, mode: "managed" },
});
// To turn coaching off:
await client.labs.agents.update("northline-intake", { supervisor: false });
```

```python
client.labs.agents.update("northline-intake", supervisor={"enabled": True, "mode": "managed"})
# To turn coaching off:
client.labs.agents.update("northline-intake", supervisor=False)
```

Use `supervisor=True` / `true` to enable the saved Supervisor profile without
requesting a switch to managed mode. These updates change the stored agent
configuration; they are not a mid-call control. See
[Supervisor models and BYOK](supervisor-models.md) for choosing a reasoning model.

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

The saved Supervisor configuration, generated/custom stage plan and team remain
on the agent when its speaking selection changes. `apply` changes only the
speaking selection; it does not enable, disable or replace the Supervisor. Active calls keep their frozen workflow. Opt-in
native live switching uses a separate allowed-model broker policy; it does not
change what `apply` means. See [Shared runtime, Manager and teams](shared-agent-runtime.md).

## Method contract

| Operation | TypeScript | Python | Meaning |
| --- | --- | --- | --- |
| Create supervised agent | `engine.create({name: "...", supervisor: true})` | `engine.create(name="...", supervisor=True)` | Create through Agent Factory using this provider selection and hosted coaching |
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
the connection. Supafone advances its shared custom stages through validated tool
results, not a persona rewrite. All five hosted speaking families support
Supervisor when enabled and configured. Native guidance uses `check_guidance`;
Hydra supplies model-reported context, not live transcripts. The shared runtime
adds custom stages, Manager reasoning and specialist consultation across all
five speaking families. Native sessions support opt-in recording, public
widgets, carrier controls and an opt-in broker for allowed native-model
handoffs. Post-call transcription needs recorded audio and the server's
Deepgram connection. Ultravox retains compatible external TTS and its opt-in
language/voice profile router. See [Shared runtime, Manager and teams](shared-agent-runtime.md) for the exact limits;
provider support is not a promise of identical voice or carrier capabilities. See the [native model matrix and limits](realtime-agent-factory.md).

A key's presence is not proof of model permissions or successful calls. Check
runtime status and validate browser and carrier behavior in the actual
deployment. [Managed credentials and BYOK](https://labs.supafone.ai/docs/byok-providers/) explain who
supplies the selected provider's key.
