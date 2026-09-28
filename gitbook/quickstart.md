# Quickstart

**Dashboard:** open [Supafone agents](https://app.supafone.ai/app/agents),
select your agent, and use its native realtime model controls. The older
[Labs workspace](https://labs.supafone.ai/builder.html) is the managed Ultravox
compatibility builder and links to these S2S controls.

Create an Agent Factory agent, preview it in the browser, then switch its
speech-to-speech model through the same Supafone harness.

Need a specific Cartesia, ElevenLabs, or Inworld voice? Start with [Ultravox + custom TTS](voice-output-modes.md). It uses the same shared S2S interface and preserves the existing managed-agent option. The native example below uses its model’s own voice.

## 1. Install and authenticate

```bash
pip install supafone-labs
npm i supafone-labs
export SUPAFONE_TOKEN=sl_live_...
```

[Create a Supafone key](https://labs.supafone.ai/console.html?mode=register).
One `sl_` key authenticates Labs Cloud and the hosted-agent API when your
Supafone product account uses the same email. See [API keys](api-keys-and-auth.md)
for account linking and scoped `sf_` keys.

## 2. Check the selected model's readiness

```bash
curl 'https://api.supafone.ai/api/v1/labs/runtime?provider=smallest' \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"
```

Use the configured Supafone platform key by default. An existing account BYOK
key overrides it for the selected provider. Status reports `source: platform`,
`account`, `none`, or `invalid`; a missing key requires setup before a live
call. You only need to supply an OpenAI, Google, xAI, or Smallest AI key when choosing BYOK
or when the platform has no key for that provider. Provider access still needs
a live preview test.

## 3. Create a native S2S agent

All five speaking families use the shared `SupafoneS2S` interface. Start with
Hydra here, or choose `OpenAIS2S`, `GeminiS2S`, `GrokS2S`, or the default
`UltravoxS2S`. The provider object creates an ordinary Agent Factory agent.
See [the shared interface](unified-s2s.md) for the complete contract.

TypeScript:

```ts
import { Supafone, HydraS2S } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN! });
const engine = new HydraS2S(supafone, { model: "hydra-v1.1", voice: "maya" });
const agent = await engine.create({
  agentKey: "northline-intake",
  name: "Northline intake",
  description: "Understand the request and book the right next step.",
});
const preview = await engine.testCall("northline-intake");
```

Python:

```python
import os
from supafone_labs import Supafone, HydraS2S

supafone = Supafone(api_key=os.environ["SUPAFONE_TOKEN"])
engine = HydraS2S(supafone, model="hydra-v1.1", voice="maya")
agent = engine.create(
    agentKey="northline-intake",
    name="Northline intake",
    description="Understand the request and book the right next step.",
)
preview = engine.test_call("northline-intake")
```

`testCall` creates a session ticket; it does not play audio by itself. Open the
agent's browser preview in the dashboard, or connect your audio client using
the [native browser transport contract](realtime-agent-factory.md#browser-preview).
Provider keys remain on the server. Creating a browser preview does not buy a
number or place a phone call.

## 4. Switch the speaking model

```ts
import { OpenAIS2S } from "supafone-labs";

const next = new OpenAIS2S(supafone, { model: "gpt-realtime-2.1", voice: "marin" });
await next.apply("northline-intake");
const nextPreview = await next.testCall("northline-intake");
```

```python
from supafone_labs import OpenAIS2S

next_engine = OpenAIS2S(supafone, model="gpt-realtime-2.1", voice="marin")
next_engine.apply("northline-intake")
next_preview = next_engine.test_call("northline-intake")
```

The same method selects Gemini, Grok, or another Hydra version. To return to
the managed default, apply `UltravoxS2S`. Provider objects share `SupafoneS2S`;
check [all five classes and their defaults](unified-s2s.md#provider-classes).

`apply` changes the next session; `testCall` / `test_call` previews the saved
agent without applying a selection itself. The same agent keeps its number,
supported tools, and fixed native stages. Model voices and capabilities vary:
Hydra has no native transcripts and cannot change persona or voice mid-session.

## 5. Connect a phone transport

Choose Supafone-managed phone, Twilio, Telnyx, Plivo, or SIP. Managed phone
uses the platform's configured carrier infrastructure and an approved number.
BYO carriers use the account's own credentials and caller ID. Verify inbound
webhooks or outbound routing before testing a real call. Follow the
[carrier setup guide](realtime-agent-factory.md#phone-calls-and-carrier-selection).

Native S2S supports intake → booking → confirmation and allowed server tools.
Set `supervisor: true` on the agent to enable coaching across all five speaking
families. Native guidance arrives through `check_guidance`; Hydra uses
model-reported context, not transcripts. Configure the Supervisor model
credentials separately from the speaking model.
It does not currently support recording, human transfer,
specialist-team handoff, DTMF navigation, public widgets, or live language/voice
profile switching.

## Managed compatibility Agent Factory Agent

Omitting `realtime` keeps the existing managed Ultravox runtime. Use that path
when you need its broader planner, compatible voice catalog, recording,
Supervisor, transfer, or widget features. See [Agent Factory](agent-factory.md)
and [Hosted Agent Builder](hosted-agent-builder.md).

## Supervise an Existing Familiar Framework

Supafone Supervisor separately observes supported existing agent stacks:

```python
import supafone_labs

brain = supafone_labs.supercharge(my_agent)
result = await brain.observe(raw_platform_event)
```

Use the [framework coverage matrix](framework-support.md) to determine whether
your adapter can send guidance or only observe. For hosted native S2S, use
the agent's `supervisor` setting instead; the shared relay delivers coaching
through `check_guidance` when supervision is enabled and credentials are ready.
