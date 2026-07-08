# Developer Workflows

Supafone Labs has two equal product pillars. Keep them mentally separate, then
combine them when the user wants the complete product.

## Pillar 1: Provider-Agnostic Framework

Use this path when the developer already has an agent running on Ultravox,
Vapi, Retell, ElevenLabs, OpenAI Realtime, Grok, Bland, LiveKit, Pipecat,
Twilio media streams, SIP, or a custom stack.

```python
import supafone_labs

brain = supafone_labs.supercharge(my_agent)
```

The framework watches call events, transcripts, tool outcomes, and call state,
then emits a silent directive only when the live agent needs help. The caller
does not hear the directive. If the watcher is disabled, out of balance, or
times out, the call continues without intervention.

## Pillar 2: Hosted Agent Factory

Use this path when the developer wants Supafone to create the agent, phone
number, voice, stages, logs, widget, and optional watcher.

This path should feel like Stripe Checkout for voice agents: one Supafone API
key first, working agent first, provider credentials only when the user chooses
advanced BYOK.

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_API_KEY!,
});

const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake",
  name: "Northline intake",
  assistantName: "Maya",
  websiteUrl: "https://northline.example",
  number: { search: { areaCode: "415" } },
  labs: { enabled: true, model: "gemma" },
});
```

Python has the matching hosted-agent helpers:

```python
from supafone_labs import Supafone

supafone = Supafone(api_key="sf_live_...")

agent = supafone.labs.agents.create_inbound_with_number({
    "agentKey": "northline-intake",
    "name": "Northline intake",
    "assistantName": "Maya",
    "websiteUrl": "https://northline.example",
    "number": {"search": {"areaCode": "415"}},
    "labs": {"enabled": True, "model": "gemma"},
})
```

## Which One Should the UI Lead With?

The hosted builder should lead with the Supafone API key because that is the
lowest-friction happy path:

1. Paste `SUPAFONE_API_KEY`.
2. Choose inbound or outbound.
3. Describe the agent.
4. Pick a voice and preview it.
5. Keep Supafone-managed providers or open advanced BYOK.
6. Create the agent and number.
7. Stream logs.
8. Export TypeScript and Python code.

The BYOK panel should be advanced. Developers should not need Twilio, Telnyx,
Plivo, SignalWire, SIP, Ultravox, Retell, Vapi, Bland, LiveKit, Pipecat,
Cartesia, Inworld, ElevenLabs, Deepgram, OpenAI, Anthropic, or xAI keys to
launch the default agent.

When BYOK is selected, group it into three lanes:

| Lane | Examples |
| --- | --- |
| Agent/provider stack | Ultravox, Retell, Vapi, Bland, LiveKit, Pipecat, GPT Realtime, Grok |
| Telephony | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks |
| TTS | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS |

## Key Routing

| Work | Key | Base URL |
| --- | --- | --- |
| Agent Factory, numbers, hosted voices | `sf_live_...` | `https://api.supafone.ai/api/v1/labs` |
| Oracle, TTS previews, STT, usage, logs | `sl_live_...` | `https://api.labs.supafone.ai` |

Some development environments may use one key for both surfaces, but production
docs and UI should show the two surfaces explicitly.

## Export Contract

Every builder-created agent should be exportable as:

- TypeScript SDK code,
- Python SDK code,
- raw REST/curl,
- JSON configuration.

The export should contain the exact choices from the UI, including direction,
voice, number strategy, `labs.enabled`, `labs.mode`, BYOK providers, tools, and
stage preset.
