# 🗣️ Voices and Previews

The builder and SDKs should make voice selection feel instant: list all voices,
filter by provider, preview audio, then export the selected voice into code.

## Hosted Agent Voice Catalog

Use the hosted-agent API when the voice belongs to the durable agent:

```ts
const voices = await supafone.labs.voices.list({ provider: "cartesia" });
```

REST:

```bash
curl "https://api.supafone.ai/api/v1/labs/voices?provider=cartesia" \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"
```

The response includes provider metadata, whether the account is
Supafone-managed, and whether developer provider keys are required.

## Labs Cloud Voice Catalog

Use Labs Cloud when the UI is previewing speech or building a playground:

```ts
const voiceIds = await supafone.voices();
```

REST:

```bash
curl https://api.labs.supafone.ai/v1/voices
```

## Preview in TypeScript

```ts
const audio = await supafone.tts(
  "Hi, this is Maya from Northline. How can I help?",
  "cartesia:sonic-warm"
);

await fs.promises.writeFile("preview.wav", audio);
```

Browser preview:

```ts
const bytes = await supafone.tts("How can I help?", selectedVoice);
const blob = new Blob([bytes], { type: "audio/mpeg" });
const url = URL.createObjectURL(blob);
new Audio(url).play();
```

## Preview in Python

Python can use the hosted TTS provider surface:

```python
import asyncio
import os
from supafone_labs import SupafoneLabsTTS

async def main():
    os.environ["SUPAFONE_LABS_API_KEY"] = "sl_live_..."
    tts = SupafoneLabsTTS(voice="cartesia:sonic-warm")
    audio = await tts.synthesize(
        "Hi, this is Maya from Northline. How can I help?"
    )
    with open("preview.wav", "wb") as f:
        f.write(audio)

asyncio.run(main())
```

If a Python app only needs the catalog today, call the REST endpoint directly:

```python
import json
import urllib.request

with urllib.request.urlopen("https://api.labs.supafone.ai/v1/voices") as response:
    voices = json.loads(response.read().decode("utf-8"))["voices"]
```

## Provider Labels

Use stable provider keys in exported config:

| Provider | Voice config example |
| --- | --- |
| Cartesia | `{ "provider": "cartesia", "voiceId": "sonic-warm" }` |
| ElevenLabs | `{ "provider": "elevenlabs", "voiceId": "rachel" }` |
| Inworld | `{ "provider": "inworld", "voiceId": "inworld-voice" }` |
| Deepgram | `{ "provider": "deepgram", "voiceId": "aura-2-thalia-en" }` |

The frontend can show logos and friendly names, but exported code should use
stable provider ids and voice ids.
