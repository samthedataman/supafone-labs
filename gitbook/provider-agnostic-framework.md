# 🔀 Provider-Agnostic Framework

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
context or receives it through the provider's native control channel. That
channel is one of two silent-injection modes — **Mode A**, a native silent
event on a speech-to-speech model, or **Mode B**, splicing a `system`/`developer`
message into the prompt when Supafone owns the pipeline LLM. Ten frameworks
expose one; Bland exposes neither. The exact primitive per framework, and the
honest "possible vs turnkey today" caveats, are in
[Framework Support (Silent Injection)](framework-support.md).

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

For Supafone's own hosted runtime, Ultravox is available **managed or BYOK**:
keep Supafone's platform Ultravox key (managed billing), or connect your own so
the agent is both placed and monitored on your account (`runtime_mode: "byok"`).
Connect it at agent create under `byok.ultravox`, or later via
`PUT /api/v1/labs/runtime`. The other hosted runtimes (Vapi, Retell, Bland,
LiveKit, Pipecat) are still coming soon. See
[BYOK Providers](byok-providers.md) and [Hosted Agents API](hosted-agents-api.md).

BYOK is not one thing. It is three independent lanes:

| Lane | Examples | Notes |
| --- | --- | --- |
| Agent/provider stack | Ultravox, Retell, Vapi, LiveKit, Pipecat, GPT Realtime, Grok, Gemini Live, Bland | The agent receives Supafone silent directives on every framework here **except Bland** — Bland's live-call API is closed (no mid-call inject, no custom-LLM), so it can be observed and scored but not whispered to live. See [Framework Support](framework-support.md). |
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
| Realtime model APIs | OpenAI Realtime, Grok, Gemini Live |
| Voice infrastructure | LiveKit, Pipecat, Twilio media streams, SIP/generic |
| TTS/STT providers | Deepgram, Cartesia, ElevenLabs, Inworld |

Each adapter reports what it supports, including whether it can update stageful
session context directly or needs a generic prompt/message injection. The
**Bland** adapter is honest about being observe-only: it parses transcripts and
scores calls but declares no live-injection capability, because the vendor
exposes no mid-call channel (see [Framework Support](framework-support.md)).

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
