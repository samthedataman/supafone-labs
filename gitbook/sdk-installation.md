# SDK Installation

Python and TypeScript expose the same hosted S2S harness: create an Agent
Factory agent with `realtime: { provider, model, voice }`, preview it, and
update the selection for the next session. Start with your Supafone API key;
configured platform model keys are used unless the account supplies BYOK.
The SDK sends the configuration to Supafone's server; installing the package
does not itself host the model or provision provider credentials.

[Create and switch an S2S agent](quickstart.md) · [Runtime limits](realtime-agent-factory.md#feature-boundaries)

Supafone Labs publishes a Python package and an unscoped TypeScript package.
The current release is **0.6.2** for both
[PyPI](https://pypi.org/project/supafone-labs/) and
[npm](https://www.npmjs.com/package/supafone-labs).

The 0.6.2 release includes native realtime Agent Factory selection in both SDKs. Install from [PyPI](https://pypi.org/project/supafone-labs/0.6.2/) or [npm](https://www.npmjs.com/package/supafone-labs/v/0.6.2), then follow [Native Realtime Agent Factory](realtime-agent-factory.md).

## Python

```bash
pip install supafone-labs
```

Recommended full install for hosted cloud, HTTP, STT, and server helpers:

```bash
pip install "supafone-labs[all]"
```

Native S2S usage:

```python
import os
from supafone_labs import Supafone

sf = Supafone(api_key=os.environ["SUPAFONE_TOKEN"])
agent = sf.labs.agents.create_inbound({
    "agentKey": "intake",
    "name": "Intake",
    "realtime": {"provider": "openai", "model": "gpt-realtime-2.1", "voice": "marin"},
})
```

### Separate Supervisor integration

Explicit usage:

```python
from supafone_labs import SupafoneLabs

brain = SupafoneLabs(
    provider="ultravox",
    llm="hosted",
    agent_label="intake",
)
```

Environment:

```bash
export SUPAFONE_LABS_API_KEY=sl_live_...
```

If no Labs key is present, use BYO provider keys such as `ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, `XAI_API_KEY`, or local fake providers for tests.

### Supervisor provider and controls

On the managed compatibility runtime, `labs.enabled: true` attaches the
model-agnostic Supervisor. Native S2S does not currently attach it. A Supafone
`sl_...` key can use a managed Supervisor model; BYOK can use Claude, OpenAI,
Gemini, OpenRouter, Groq, or Cerebras. The speaking agent and Supervisor model
are independent.

```python
from supafone_labs import SupafoneLabs
from supafone_labs.config import Settings

supervisor = SupafoneLabs(
    provider="ultravox",       # speaking-agent adapter
    llm="anthropic",           # supervisor provider
    supervisor_model="claude-haiku-4-5-20251001",
    config=Settings(
        confidence_threshold=0.65,
        supervisor_timeout_seconds=5.0,
    ),
    supervisor_instructions="Prioritize empathy, tool truth, and the next required intake step.",
    scenario="intake",
    mode="apply",
    telemetry=True,
    post_call_analysis=True,
)
```

The older `oracle_model`, `oracle_timeout_seconds`, and `oracle_instructions`
names remain deprecated compatibility aliases. New code should use the
Supervisor names above. See [Supervisor Models: Managed and BYOK](supervisor-models.md)
and [Programmable Supervisor Directives](programmable-supervisor-directives.md).

For raw hosted completions, both SDKs expose `model`, `max_tokens`/
`maxTokens`, and `temperature`. `whisper()` additionally accepts operator
`guardrails`. The full supervisor also accepts custom belief/directive prompts,
an injection adapter, telemetry and post-call controls, and an `agent_label`
for optimization history.

## TypeScript

```bash
npm i supafone-labs
```

ESM:

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY!,
});
```

CommonJS:

```js
const { Supafone } = require("supafone-labs");
```

Hosted-agent usage — since 0.4.4 a lone `sl_` key cross-fills every credential
lane (labs, hosted-agent, and account) automatically:

```ts
const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_TOKEN!, // sl_live_... — one key, both APIs
});
```

Explicit per-surface keys are still supported when you want them scoped:

```ts
const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY!,
  supafoneApiKey: process.env.SUPAFONE_API_KEY!,
  supafoneApiBaseUrl: "https://api.supafone.ai",
});
```

The package works in Node 18+ and browsers using native `fetch`. Live STT needs
a global `WebSocket`; on older Node versions, pass a WebSocket implementation.

Hosted Agent Factory creation can also opt into same-call language and voice
routing. See [Live Language and Voice Routing](live-language-voice-routing.md)
for the shared TypeScript, Python, REST, and MCP contract.

```ts
import WebSocket from "ws";

const live = supafone.liveTranscribe({
  WebSocketImpl: WebSocket,
  language: "multi",
  onResult: (r) => console.log(r.transcript)
});
```

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
