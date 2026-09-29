# Quickstart

**One S2S routing hub, with Supervisor alongside your speaking model.**
Create a supervised agent with one Supafone key, then choose Ultravox, OpenAI,
Gemini, Grok or Smallest AI Hydra. Prefer your own provider accounts? You can
[bring speaking and Supervisor keys independently](https://labs.supafone.ai/docs/byok-providers/).

## 1. Install and add your Supafone key

Choose your SDK:

```bash
pip install supafone-labs==0.7.2
npm install supafone-labs@0.7.2
```

[Create a Supafone key](https://labs.supafone.ai/console.html?mode=register)
and set `SUPAFONE_API_KEY` in your server environment.

## 2. Create a supervised agent

Python:

```python
import os
from supafone_labs import Supafone, SupafoneS2S

client = Supafone(api_key=os.environ["SUPAFONE_API_KEY"])
engine = SupafoneS2S(client, provider="openai")
agent = engine.create(
    agent_key="front-desk", name="Front desk",
    description="Help callers and book the right next step.",
    supervisor=True,
)
```

TypeScript:

```ts
import { Supafone, SupafoneS2S } from "supafone-labs";

const client = new Supafone({ apiKey: process.env.SUPAFONE_API_KEY! });
const engine = new SupafoneS2S(client, { provider: "openai" });
const agent = await engine.create({
  agentKey: "front-desk", name: "Front desk",
  description: "Help callers and book the right next step.",
  supervisor: true,
});
```

The constructor chooses the speaking model. `supervisor=True` / `true` adds
hosted coaching to the agent; no separate Supervisor client is needed.
Creating the agent saves its configuration without starting a call.

## 3. Check readiness and try a browser call

The one-key path uses Supafone's configured provider and Supervisor credentials.
An existing account speaking key takes priority. Check the selected provider
before connecting audio:

```python
status = client.labs.runtime.get(provider="openai")
preview = engine.test_call("front-desk")
```

```ts
const status = await client.labs.runtime.get({ provider: "openai" });
const preview = await engine.testCall("front-desk");
```

Read `source` and `connected` in the returned status. Missing platform keys
require setup or [BYOK](https://labs.supafone.ai/docs/byok-providers/) before a
live call. A configured key still needs the provider's model permissions.
Supervisor credentials and carrier readiness are checked separately.

`testCall` / `test_call` creates a browser-session ticket. Use the agent's
preview in [Agent Factory](https://app.supafone.ai/app/agents) or connect an
audio client with the [browser transport contract](realtime-agent-factory.md#browser-preview).
The ticket does not play audio by itself, buy a number or place a phone call.
Browser sessions can consume managed minutes.

## 4. Switch the speaking model

```python
next_engine = SupafoneS2S(client, provider="google")
next_engine.apply("front-desk")
next_preview = next_engine.test_call("front-desk")
```

```ts
const next = new SupafoneS2S(client, { provider: "google" });
await next.apply("front-desk");
const nextPreview = await next.testCall("front-desk");
```

Use `ultravox`, `openai`, `google`, `xai` or `smallest`. `apply` changes the
saved selection for the next session and keeps the agent's Supervisor profile,
number, supported tools, team and custom stages. Preview uses the saved
selection; it does not apply a model change itself.

Choose a voice supported by the new model. Hydra has no native transcripts
and keeps its persona and voice fixed during a session. For Cartesia,
ElevenLabs or Inworld voices, use [Ultravox + custom TTS](voice-output-modes.md).
See [all provider classes and defaults](unified-s2s.md#provider-classes).

## 5. Connect a phone transport

Choose Supafone-managed phone, Twilio, Telnyx, Plivo, or SIP. Managed phone
uses the platform's configured carrier infrastructure and an approved number.
BYO carriers use the account's own credentials and caller ID. Verify inbound
webhooks or outbound routing before testing a real call. Follow the
[carrier setup guide](realtime-agent-factory.md#phone-calls-and-carrier-selection).

Native S2S and Ultravox share the 3–8 stage planner, configured server tools,
saved facts and successful tool receipts. Set `supervisor: true` to request
coaching and `manager: true` for bounded workflow reasoning. Both require
configured reasoning credentials. Native guidance uses `check_guidance`;
Hydra supplies model-reported context, not transcripts.

Native calls support opt-in recording, public widgets, configured carrier
controls and separate opt-in native-model handoff. Hydra has no live transcript
stream; post-call transcription requires recorded audio and the server's
Deepgram connection. See [Shared runtime, Manager and teams](shared-agent-runtime.md) before enabling these features.

## Managed compatibility Agent Factory Agent

Omitting `realtime` keeps the existing managed Ultravox runtime. It uses the
shared Agent Factory workflow and retains compatible external TTS voices and
its opt-in language/voice profile routing. See [Agent Factory](https://labs.supafone.ai/docs/agent-factory/)
and [Hosted Agent Builder](https://labs.supafone.ai/docs/hosted-agent-builder/).

## Supervise an Existing Familiar Framework

Supafone Supervisor separately observes supported existing agent stacks:

```python
import supafone_labs

brain = supafone_labs.supercharge(my_agent)
result = await brain.observe(raw_platform_event)
```

Use the [framework coverage matrix](https://labs.supafone.ai/docs/framework-support/) to determine whether
your adapter can send guidance or only observe. For hosted native S2S, use
the agent's `supervisor` setting instead; the shared relay delivers coaching
through `check_guidance` when supervision is enabled and credentials are ready.
