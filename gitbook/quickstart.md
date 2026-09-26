# Quickstart

**Dashboard:** open [Supafone agents](https://app.supafone.ai/app/agents),
select your agent, and use its native realtime model controls. The older
[Labs workspace](https://labs.supafone.ai/builder.html) is the managed Ultravox
compatibility builder and links to these S2S controls.

Create an Agent Factory agent, preview it in the browser, then switch its
speech-to-speech model through the same Supafone harness.

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
curl 'https://api.supafone.ai/api/v1/labs/runtime?provider=openai' \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"
```

Use the configured Supafone platform key by default. An existing account BYOK
key overrides it for the selected provider. Status reports `source: platform`,
`account`, `none`, or `invalid`; a missing key requires setup before a live
call. You only need to supply an OpenAI, Google, or xAI key when choosing BYOK
or when the platform has no key for that provider. Provider access still needs
a live preview test.

## 3. Create a native S2S agent

TypeScript:

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN! });
const agent = await supafone.labs.agents.createInbound({
  agentKey: "northline-intake",
  name: "Northline intake",
  description: "Understand the request and book the right next step.",
  realtime: { provider: "openai", model: "gpt-realtime-2.1", voice: "marin" },
  telephony: { mode: "supafone_managed", provider: "supafone" },
});
const preview = await supafone.labs.agents.testCall("northline-intake");
console.log(preview.browser_session);
```

Python:

```python
import os
from supafone_labs import Supafone

supafone = Supafone(api_key=os.environ["SUPAFONE_TOKEN"])
agent = supafone.labs.agents.create_inbound({
    "agentKey": "northline-intake",
    "name": "Northline intake",
    "description": "Understand the request and book the right next step.",
    "realtime": {"provider": "openai", "model": "gpt-realtime-2.1", "voice": "marin"},
    "telephony": {"mode": "supafone_managed", "provider": "supafone"},
})
preview = supafone.labs.agents.test_call("northline-intake")
print(preview["browser_session"])
```

`testCall` creates a session ticket; it does not play audio by itself. Open the
agent's browser preview in the dashboard, or connect your audio client using
the [native browser transport contract](realtime-agent-factory.md#browser-preview).
Provider keys remain on the server. Creating a browser preview does not buy a
number or place a phone call.

## 4. Switch the speaking model

```ts
await supafone.labs.agents.update("northline-intake", {
  realtime: { provider: "google", model: "gemini-3.1-flash-live-preview", voice: "Puck" },
});
const nextPreview = await supafone.labs.agents.testCall("northline-intake");
```

```python
supafone.labs.agents.update("northline-intake", {
    "realtime": {"provider": "xai", "model": "grok-voice-latest", "voice": "eve"},
})
next_preview = supafone.labs.agents.test_call("northline-intake")
```

OpenAI `gpt-live-1` is also available with `marin`. Check the new provider's
readiness first. The new selection applies to the next session; the harness
keeps the agent configuration, supported tools, fixed three stages, and phone
configuration. Voices and model behavior remain provider-specific.

## 5. Connect a phone transport

Choose Supafone-managed phone, Twilio, Telnyx, Plivo, or SIP. Managed phone
uses the platform's configured carrier infrastructure and an approved number.
BYO carriers use the account's own credentials and caller ID. Verify inbound
webhooks or outbound routing before testing a real call. Follow the
[carrier setup guide](realtime-agent-factory.md#phone-calls-and-carrier-selection).

Native S2S supports intake → booking → confirmation and allowed server tools.
It does not currently support recording, Supervisor coaching, human transfer,
DTMF navigation, public widgets, or live language/voice profile switching.

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
your adapter can send guidance or only observe. This integration does not
turn on Supervisor coaching in the native S2S harness.
