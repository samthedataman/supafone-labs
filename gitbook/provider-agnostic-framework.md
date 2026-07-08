# Provider-Agnostic Framework

The provider-agnostic framework is the self-healing Supafone Labs watcher. It
is the "supercharge" path: it upgrades an agent the developer already runs
instead of forcing them into Supafone-hosted telephony or a hosted Supafone
agent.

```python
import supafone_labs

brain = supafone_labs.supercharge(
    my_agent,
    scenario="legal_intake",
)
```

## What It Does

1. Normalize vendor events into canonical call events.
2. Maintain deterministic runtime state such as stage, consent, tool state,
   caller intent, and risk flags.
3. Run the oracle only when supervision is enabled.
4. Emit a silent directive or provider-native action.
5. Log the decision, latency, provider, model, and billing metadata.

The caller never hears the directive directly. The live agent reads it as
context or receives it through the provider's native control channel.

## Labs Must Be Explicit

Hosted agents and builder UI should only instantiate the watcher when
`labs.enabled` is true.

```json
{
  "labs": {
    "enabled": true,
    "mode": "supafone_managed",
    "model": "gemma"
  }
}
```

When `labs.enabled` is false or omitted, create the agent without the Supafone
watcher sidecar. Do not silently turn it on because the user selected a voice
provider or telephony provider.

## Managed vs BYOK

Supafone-managed mode:

```json
{
  "labs": {
    "enabled": true,
    "mode": "supafone_managed",
    "managedInfrastructure": true
  }
}
```

BYOK mode:

```json
{
  "labs": {
    "enabled": true,
    "mode": "byok",
    "managedInfrastructure": false,
    "stt": { "provider": "deepgram", "model": "nova-3" },
    "llm": { "provider": "openai", "model": "gpt-4.1-mini" },
    "tts": { "provider": "elevenlabs" }
  }
}
```

Use Supafone-managed mode as the default. Use BYOK when the customer already
owns vendor accounts or wants vendor-specific control.

BYOK is not one thing. It is three independent lanes:

| Lane | Examples | Notes |
| --- | --- | --- |
| Agent/provider stack | Ultravox, Retell, Vapi, Bland, LiveKit, Pipecat, GPT Realtime, Grok | The agent still receives Supafone silent directives. |
| Telephony | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks | Carrier credentials and call routing stay in the customer's account. |
| TTS | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS | Voice rendering can be managed or customer-owned. |

The framework should accept mixed deployments. A customer might use BYOK
Telnyx, managed Labs watcher, and BYOK ElevenLabs. Another might bring
Ultravox and Twilio while using Supafone only for call-state supervision,
directives, logs, QA, and optimizer output.

## Adapter Families

The public runtime includes adapters for:

| Family | Examples |
| --- | --- |
| Realtime agent platforms | Ultravox, Vapi, Retell, Bland |
| Realtime model APIs | OpenAI Realtime, Grok |
| Voice infrastructure | LiveKit, Pipecat, Twilio media streams, SIP/generic |
| TTS/STT providers | Deepgram, Cartesia, ElevenLabs, Inworld |

Each adapter reports what it supports, including whether it can update stageful
session context directly or needs a generic prompt/message injection.

## Event Loop

```python
brain = supafone_labs.SupafoneLabs(
    provider="ultravox",
    llm="hosted",
    agent_label="intake",
)

async def on_platform_event(raw_event):
    result = await brain.observe(raw_event)
    for action in result.actions:
        await deliver_to_voice_platform(action)
```

The deterministic runtime can still emit policy decisions even if the LLM
oracle is unavailable. That is the degrade-safe path.
