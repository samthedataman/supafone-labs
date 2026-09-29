# SDK Installation

Use Supafone as an **S2S routing hub with Supervisor**: choose the speaking
model, then let a separate reasoning model guide the call. The supported
families are **Ultravox, OpenAI, Gemini, Grok and Smallest AI Hydra**.

Start with **one Supafone API key**, or [bring your own speaking-model and
Supervisor keys](byok-providers.md). You choose each independently.

## Create a supervised S2S agent

Pass `supervisor=True` / `true` to `SupafoneS2S.create()`. The constructor
chooses the speaking provider; `create` saves the agent and its coaching setting.

### Install

The Python SDK, CLI and TypeScript SDK use **0.7.2**.

```bash
python -m pip install --upgrade supafone-labs==0.7.2
npm install supafone-labs@0.7.2
```

Set your Supafone account key as `SUPAFONE_API_KEY` in your server environment.

### Python

```python
import os
from supafone_labs import Supafone, SupafoneS2S

client = Supafone(api_key=os.environ["SUPAFONE_API_KEY"])
engine = SupafoneS2S(client, provider="openai")

agent = engine.create(
    agent_key="front-desk",
    name="Front desk",
    description="Help callers and book the right next step.",
    supervisor=True,
)
```

### TypeScript

```ts
import { Supafone, SupafoneS2S } from "supafone-labs";

const client = new Supafone({ apiKey: process.env.SUPAFONE_API_KEY! });
const engine = new SupafoneS2S(client, { provider: "openai" });

const agent = await engine.create({
  agentKey: "front-desk",
  name: "Front desk",
  description: "Help callers and book the right next step.",
  supervisor: true,
});
```

Use `provider="ultravox"`, `"openai"`, `"google"`, `"xai"`, or `"smallest"`
in Python, or the corresponding `provider` value in TypeScript. You can also
choose the provider subclass. Model and native voice options remain on the
S2S constructor. See [the shared S2S interface](unified-s2s.md) for the catalog.

**Put `supervisor` on `create()`, not on the S2S constructor.** This is an
agent setting saved by the hosted Agent Factory, independently of its speaking
model. Creating the configuration does not start a call.

## Turn Supervisor on for an existing agent

Use the same client to update the saved agent:

```python
client.labs.agents.update("front-desk", supervisor=True)
# Disable it explicitly:
client.labs.agents.update("front-desk", supervisor=False)
```

```ts
await client.labs.agents.update("front-desk", { supervisor: true });
// Disable it explicitly:
await client.labs.agents.update("front-desk", { supervisor: false });
```

These updates configure subsequent calls. Switching the speaking provider with
`engine.apply("front-desk")` preserves the saved Supervisor setting; `apply()`
only changes the speaking selection. It does not enable supervision on an
existing agent whose Supervisor is disabled.

## Managed defaults and your own reasoning model

New agents inherit `Supafone`'s `supervisor` default, which is `true`. The
explicit flag above makes that choice visible. `supervisor=True` enables the
agent's default or saved Supervisor profile; it does not replace an existing
BYOK profile. To explicitly select Supafone-managed reasoning, use:

```python
agent = engine.create(
    name="Managed front desk",
    supervisor={"enabled": True, "mode": "managed"},
)
# The same object works with client.labs.agents.update(...).
```

```ts
const managedAgent = await engine.create({
  name: "Managed front desk",
  supervisor: { enabled: true, mode: "managed" },
});
```

The speaking model and reasoning model are independent. Optional BYOK
Supervisor profiles support Anthropic, OpenAI, Gemini, OpenRouter, Groq, and
Cerebras. [Choose managed or BYOK reasoning](supervisor-models.md).

Managed operation requires the corresponding keys on Supafone's server. An
account's saved speaking-provider key takes priority over its platform default.
Installing an SDK does not configure keys or deploy the hosted runtime.
**Hosted readiness:** Ultravox uses its managed supervision path; native S2S
uses the shared call relay and guidance tools. Check
`client.labs.capabilities()` and agent readiness before a live call; a saved
`supervisor` flag alone is not evidence that coaching ran.

For advanced workflows, [Manager and specialist teams](shared-agent-runtime.md)
add bounded reasoning and stage coordination above the speaking agent.
Supervisor guidance and Manager coordination are separate controls.

## Use platform keys or bring your own speaking key

Ultravox, OpenAI, Gemini, Grok and Hydra each use a saved account key when one
exists, otherwise Supafone's configured platform key. Key choice belongs to
the account runtime and is separate from Supervisor's reasoning profile.

```python
client.labs.runtime.configure(
    provider="openai", mode="byok",
    credentials={"api_key": os.environ["OPENAI_API_KEY"]},
)
status = client.labs.runtime.get(provider="openai")
```

```ts
await client.labs.runtime.configure({
  provider: "openai", mode: "byok", credentials: { apiKey: process.env.OPENAI_API_KEY! },
});
const status = await client.labs.runtime.get({ provider: "openai" });
```

Explicit `mode="supafone_managed"` / `mode: "supafone_managed"`, without
credentials, removes this provider's account override for future calls across
the account. This **0.7.2** feature requires admin permission and the matching
hosted API. [Choose keys for all five providers](byok-providers.md)
includes reset examples, the provider/key table, CLI commands and readiness.

## Test the saved agent

```python
preview = engine.test_call("front-desk")
```

```ts
const preview = await engine.testCall("front-desk");
```

Preview creates an authenticated browser session for the saved configuration;
your audio client must connect using the returned transport. It can consume
managed minutes. Provider credentials and audio remain server-managed.

Ultravox retains its compatible custom TTS options. Native models use their
own voices. Hydra has no native live transcript; its coaching context is
model-reported. See [runtime limits](realtime-agent-factory.md#feature-boundaries).

## Command-line setup

The Python package installs `supafone`; the npm package is a library.

```bash
supafone --version
supafone agents create --name "Front desk" --set agent_key=front-desk --s2s-provider openai --supervisor managed
supafone agents update front-desk --supervisor managed
```

Use the actual agent key returned by creation when updating.
[Read the CLI guide](cli.md) for stage planning, Manager controls, and provider
readiness checks.

## Integrate Supervisor with a runtime you operate

`SupafoneLabs(...)` is the separate observation and guidance interface for a
runtime you integrate yourself. It is not required for the hosted S2S examples
above. Start with [Supafone Supervisor](supafone-supervisor.md) and the
[adapter capability reference](provider-contracts.md) for that integration.

The package also provides optional HTTP, STT, and server helpers through
`pip install "supafone-labs[all]"`. TypeScript works in Node 18+ and browsers
with native `fetch`; live STT needs a global `WebSocket` or an implementation
passed by your application. Keep account keys in trusted server code.

## Universal Phone Tester

Both SDKs expose the real provider-neutral phone grader. The target can run on
Vapi, Retell, Bland, OpenAI Realtime, Grok, LiveKit, or a custom runtime, and
can use any carrier reachable over PSTN.

Python:

```python
from supafone_labs import Supafone

sf = Supafone()  # SUPAFONE_TOKEN=sl_live_...
started = sf.tester.grade_agent(
    to_number="+14155550100",
    scenario="price_probe",
    ai_provider="gpt_realtime",
    telephony_provider="twilio",
    authorized=True,
)
finished = sf.tester.wait(started["session_id"])
print(finished["verdict"], finished["transcript"])
```

TypeScript:

```ts
const started = await client.tester.gradeAgent({
  toNumber: "+14155550100",
  scenario: "price_probe",
  aiProvider: "vapi",
  telephonyProvider: "telnyx",
  authorized: true,
});
const finished = await client.tester.wait(started.session_id);
```

This places a real call and spends tester credits. Both SDKs reject missing
authorization and malformed E.164 numbers before dialing.

## Browser WebRTC calls

Earlier release `0.4.10` added first-class browser-session creation without buying or
dialing a phone number:

```ts
const started = await client.startWebRtcCall({ agentId: "agent-123" });
console.log(started.browser_session.join_url);
```

```python
started = client.start_webrtc_call(agent_id="agent-123")
print(started["browser_session"]["join_url"])
```

See [Browser WebRTC Calls](browser-webrtc-calls.md) for React integration,
security boundaries, transport details, and transfer limitations.

## Stripe-hosted billing handoff

Version `0.4.11` adds plan, credit-pack, and managed-number Checkout links to
both SDKs and the MCP server. Clients receive a public `checkout_url`; Stripe
card entry and entitlement verification remain in Supafone's private services.
See [Pricing and Credits](pricing-and-credits.md) for the full flow.

## Hosted call planning and complete REST parity

Earlier release `0.4.13` turned one plain-language description into a validated,
reviewable 3–8 stage plan through REST, Python, TypeScript, or MCP. Agent
creation installs the generated or developer-edited plan in the executable
runtime. It also completes hosted discovery, runtime, call, recording, and
transcript route parity across the public clients.

## Outbound campaigns

The same account-authenticated clients create, launch, monitor, pause, and
round-trip call campaigns as YAML. See
[Outbound Call Campaigns](outbound-call-campaigns.md) for the complete
TypeScript and Python lifecycle.

## Package Names

| Ecosystem | Install name | Import name |
| --- | --- | --- |
| Python | `supafone-labs` | `supafone_labs` |
| npm | `supafone-labs` | `Supafone` from `"supafone-labs"` |
