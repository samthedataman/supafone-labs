# Ultravox + Custom TTS and Native S2S

Agent Factory has two ways to produce a speaking agent. Both belong to the
shared `SupafoneS2S` offering and keep the same saved agent and phone assignment.

| Choice | How the voice works |
| --- | --- |
| **Ultravox + custom TTS** | Ultravox runs the conversation; a compatible TTS provider supplies speech. |
| **Native S2S** | OpenAI, Gemini, Grok, or Hydra uses its own audio output and supported voices. |

Choose Ultravox when you need a specific TTS voice and its broader managed
planner, compatible Supervisor, and hosted features. Choose native S2S for the
selected model's native conversation behavior.

The Ultravox option is the existing default Agent Factory runtime. It remains
a supported choice within the shared interface. “Managed compatibility” in
older guides refers to this same runtime; it does not mean the feature was removed.

## Understand the two audio paths

```text
Ultravox + custom TTS
Caller audio → Ultravox conversation → compatible TTS voice → caller

Native S2S
Caller audio → selected model's native audio loop → caller

Both: saved Supafone agent + supported tools/stages + browser or phone
```

The speaking runtime and synthesis provider are separate choices on Ultravox.
For example, **Ultravox + Cartesia** means Ultravox runs the conversation and
Cartesia supplies the voice. It does not select a Cartesia conversation model.

Native S2S uses `realtime.voice` from the selected model's catalog. The current
native harness does not accept Cartesia, ElevenLabs, Inworld, or arbitrary TTS
as a replacement for that audio output. Selecting an external TTS voice does
not make it compatible with every S2S model.

## What works today

| Voice source | Managed Ultravox call support |
| --- | --- |
| Ultravox catalog voices | Supported, subject to account access. |
| Cartesia | Supported through the named external-voice mapping. |
| ElevenLabs | Supported through the named external-voice mapping. |
| Inworld | Supported through the named external-voice mapping. |
| Deepgram | **Preview only** in the current hosted integration; no live-call bridge yet. |
| Custom `TTSProvider` | **Not automatically a hosted call integration**; supports developer-owned synthesis. |

Use real IDs from your account's current catalog. Check `configured`,
`runtime_selectable`, `runtime_support_reason`, and provider capabilities where
returned. A voice preview proves synthesis, not successful delivery in a call.
Missing or unknown capability must not be treated as permission to use any voice.

Ultravox itself documents additional generic external TTS integrations. Those
upstream options are not automatically exposed by Supafone's hosted runtime.
Generic TTS can also introduce buffering and approximate transcript timing.
See [Ultravox's external voice documentation](https://docs.ultravox.ai/voices/bring-your-own).

## Use custom TTS through the shared interface now

The published SDK keeps Ultravox's voice in the agent's `voice` settings.
`UltravoxS2S` does not accept native model/voice constructor options.

TypeScript:

```ts
import { Supafone, UltravoxS2S } from "supafone-labs";

const client = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN! });
const catalog = await client.labs.voices.list({ provider: "cartesia" });
console.log(catalog.voices); // choose a configured, compatible catalog voice

const engine = new UltravoxS2S(client);
await engine.create({
  agentKey: "northline-custom-voice",
  name: "Northline custom voice",
  description: "Understand the request and book the next step.",
  voice: { provider: "cartesia", voiceId: process.env.CARTESIA_VOICE_ID! },
});
const preview = await engine.testCall("northline-custom-voice");
```

Python:

```python
import os
from supafone_labs import Supafone, UltravoxS2S

client = Supafone(api_key=os.environ["SUPAFONE_TOKEN"])
catalog = client.labs.voices.list(provider="cartesia")
print(catalog["voices"])

engine = UltravoxS2S(client)
engine.create(
    agentKey="northline-custom-voice",
    name="Northline custom voice",
    description="Understand the request and book the next step.",
    voice={"provider": "cartesia", "voiceId": os.environ["CARTESIA_VOICE_ID"]},
)
preview = engine.test_call("northline-custom-voice")
```

Your Supafone application key authenticates these requests. Runtime and TTS
credentials must be configured on the server and on the relevant Ultravox
account where required. Account BYOK and platform defaults must resolve for
both the runtime and the selected voice; a working catalog preview alone is
not proof that those credentials are ready for a live call.

## Switch models and return to your custom voice

Apply a native provider for the next session:

```ts
import { OpenAIS2S } from "supafone-labs";

await new OpenAIS2S(client, { model: "gpt-realtime-2.1", voice: "marin" })
  .apply("northline-custom-voice");
```

To return, apply `UltravoxS2S`, then explicitly set the desired catalog voice
if needed:

```ts
await new UltravoxS2S(client).apply("northline-custom-voice");
await client.labs.agents.update("northline-custom-voice", {
  voice: { provider: "cartesia", voiceId: process.env.CARTESIA_VOICE_ID! },
});
```

```python
UltravoxS2S(client).apply("northline-custom-voice")
client.labs.agents.update(
    "northline-custom-voice",
    voice={"provider": "cartesia", "voiceId": os.environ["CARTESIA_VOICE_ID"]},
)
```

Changes affect new sessions. Native models use their own voices while selected.
The saved agent and phone assignment stay the same, but runtime features do
not become interchangeable: review planner stages, tools, recording,
Supervisor, transfer, and language routing before switching a production agent.
Preview the saved configuration after each change.

## Supervisor is a separate capability

On compatible managed Ultravox calls, changing the TTS provider changes the
speaking voice without replacing the Supervisor layer. Native Agent Factory
calls on OpenAI, Gemini, Grok, and Hydra do not currently have Supervisor coaching.
External SDK adapters have their own guidance and observation support; see
[Framework Coverage](https://labs.supafone.ai/docs/framework-support/).

Next: [Shared S2S Interface](unified-s2s.md),
[Dynamic Voice Catalog](https://labs.supafone.ai/docs/voice-catalog-and-selection/),
[Native S2S limits](realtime-agent-factory.md#feature-boundaries).
