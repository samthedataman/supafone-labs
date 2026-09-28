# Voices and Previews

Choose the conversation runtime first, then a voice it can actually use.
The shared S2S interface includes both [Ultravox + custom TTS and native S2S](voice-output-modes.md).

## Two different voice catalogs

| Runtime | Voice source | Where to select it |
| --- | --- | --- |
| Managed Ultravox | Compatible Ultravox, Cartesia, ElevenLabs, or Inworld catalog voices | The saved agent's `voice` object |
| Native OpenAI, Gemini, Grok, or Hydra | The selected model's own supported voices | `realtime.voice`, or the native provider class's `voice` option |

External TTS is not a voice override for the current native S2S harness.
Deepgram catalog previews and custom SDK TTS synthesis do not imply a hosted
Ultravox call bridge. Check the [runtime support details](voice-output-modes.md#what-works-today).

## Find a compatible managed voice

TypeScript:

```ts
const page = await supafone.labs.voices.list({ provider: "cartesia" });
console.log(page.voices);
```

Python:

```python
page = supafone.labs.voices.list(provider="cartesia")
print(page["voices"])
```

REST supports additional filters and pagination:

```bash
curl "https://api.supafone.ai/api/v1/labs/voices?provider=cartesia&configured_only=true" \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"
```

Read `configured`, `runtime_selectable`, `runtime_support_reason`, and provider
capabilities where returned. A configured voice can still be preview-only.
Follow `next_cursor` to read more pages. Use actual catalog IDs, not example
names, for live configuration.

[Dynamic Voice Catalog](voice-catalog-and-selection.md) documents brand metadata,
language compatibility, REST recommendations, and the published SDK boundary.

## Preview the voice, then preview the agent

A catalog preview tests synthesis of a sample phrase:

```bash
curl --get "https://api.supafone.ai/api/v1/labs/voices/preview" \
  -H "Authorization: Bearer $SUPAFONE_TOKEN" \
  --data-urlencode "voice=$CATALOG_VOICE_ID" \
  --output voice-preview.mp3
```

A full agent preview also exercises the conversation runtime and selected voice:

```ts
import { UltravoxS2S } from "supafone-labs";

await new UltravoxS2S(supafone).apply("northline-intake");
await supafone.labs.agents.update("northline-intake", {
  voice: { provider: "cartesia", voiceId: process.env.CARTESIA_VOICE_ID! },
});
const preview = await new UltravoxS2S(supafone).testCall("northline-intake");
```

```python
from supafone_labs import UltravoxS2S
import os

UltravoxS2S(supafone).apply("northline-intake")
supafone.labs.agents.update(
    "northline-intake",
    voice={"provider": "cartesia", "voiceId": os.environ["CARTESIA_VOICE_ID"]},
)
preview = UltravoxS2S(supafone).test_call("northline-intake")
```

`testCall`/`test_call` returns connection information for the saved agent.
Complete the browser session to hear it. Synthesis alone does not validate
interruptions, tools, stages, or your phone carrier.

## Standalone TTS is a separate surface

Labs Cloud's `/v1/voices`, `/v1/tts`, the client's `tts` method, and Python's
`TTSProvider` implementations support speech synthesis outside a hosted phone
call. They are useful for audio previews and developer-owned applications.
Choosing one of these backends does not replace an S2S model's native output or
install it into Agent Factory. Hosted support is listed in
[the voice-output guide](voice-output-modes.md#what-works-today).
