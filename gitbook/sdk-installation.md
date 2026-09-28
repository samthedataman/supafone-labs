# SDK Installation

## Add Supervisor to your S2S agent

Pass `supervisor=True` in Python or `supervisor: true` in TypeScript to
**`SupafoneS2S.create()`**. The same option works with `UltravoxS2S`,
`OpenAIS2S`, `GeminiS2S`, `GrokS2S`, and `HydraS2S`.

The constructor chooses the speaking model. `create()` saves the agent's job,
Supervisor setting, stages, and tools. You do not need a separate
`SupafoneLabs` object to supervise this hosted agent.

### Install

The Python SDK and CLI are **0.7.1**; the TypeScript SDK is **0.7.0**.

```bash
python -m pip install --upgrade supafone-labs==0.7.1
npm install supafone-labs@0.7.0
```

Use your Supafone account key as `SUPAFONE_API_KEY`. Provider and managed
Supervisor keys stay on Supafone's server.

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
**Hosted rollout status (September 28, 2026):** the published SDKs accept this
configuration, but the new native S2S Supervisor backend rollout is still
pending. Ultravox uses its existing managed supervision path. Check
`client.labs.capabilities()` and agent readiness before a live call; a saved
`supervisor` flag alone is not evidence that coaching ran.

For advanced workflows, [Manager and specialist teams](shared-agent-runtime.md)
add bounded reasoning and stage coordination above the speaking agent.
Supervisor guidance and Manager coordination are separate controls.

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
const started = await supafone.tester.gradeAgent({
  toNumber: "+14155550100",
  scenario: "price_probe",
  aiProvider: "vapi",
  telephonyProvider: "telnyx",
  authorized: true,
});
const finished = await supafone.tester.wait(started.session_id);
```

This places a real call and spends tester credits. Both SDKs reject missing
authorization and malformed E.164 numbers before dialing.

## Browser WebRTC calls

Earlier release `0.4.10` added first-class browser-session creation without buying or
dialing a phone number:

```ts
const started = await supafone.startWebRtcCall({ agentId: "agent-123" });
console.log(started.browser_session.join_url);
```

```python
started = supafone.start_webrtc_call(agent_id="agent-123")
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
