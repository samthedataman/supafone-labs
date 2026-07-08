# Supafone Labs

Supafone Labs is the developer framework behind Supafone. It gives teams two
ways to ship production voice agents:

- **Agent Factory**: create complete phone, web, and campaign agents from code
  with managed stages, voices, numbers, tools, transcripts, recordings,
  widgets, usage, and Supafone Pro watcher attached. This path is designed to
  eliminate the need for customer-owned voice-platform, telephony, TTS, STT,
  and LLM keys before launch.
- **Self-healing Labs watcher**: keep Vapi, Retell, Bland, OpenAI Realtime,
  Grok, Ultravox, LiveKit, Pipecat, SIP, Twilio, Telnyx, or another stack, then
  add the Supafone Labs second mind that listens off the hot path and sends
  silent corrective directives back to the live agent.

There are two API surfaces:

| Surface | Base URL | Key | Primary use |
| --- | --- | --- | --- |
| Labs Cloud | `https://api.labs.supafone.ai` | `sl_live_...` | Oracle, TTS, STT, logs, builder, QA, optimizer |
| Hosted Agents | `https://api.supafone.ai/api/v1/labs` | `sf_live_...` | Hosted agent, number, voice, preset, and telephony provisioning |

Use the unscoped npm package:

```bash
npm i supafone-labs
```

Use the Python package:

```bash
pip install "supafone-labs[all]"
```

The default hosted-agent path is Supafone-managed. Developers do not need to
bring Twilio, Ultravox, Cartesia, Inworld, ElevenLabs, or Deepgram accounts just
to launch an agent. Real dedicated or premium phone-number purchases should be
explicit product choices, not implicit defaults.

BYOK is split into three separate lanes:

| BYOK lane | Examples |
| --- | --- |
| Agent/provider stack | Ultravox, Retell, Vapi, Bland, LiveKit, Pipecat, GPT Realtime, Grok |
| Telephony | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks |
| TTS | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS |

Teams can use any combination of managed and BYOK. For example, they can keep
Supafone-managed telephony but bring their own ElevenLabs key, or bring Telnyx
and Cartesia while still using the managed self-healing watcher.

Start with [Developer Workflows](developer-workflows.md) and
[Quickstart](quickstart.md), then read [API Keys and Auth](api-keys-and-auth.md).
For the full builder surface, read [Agent Factory](agent-factory.md),
[Call Stages](call-stages.md), [Voices and Previews](voices-and-previews.md),
and [Log Streaming](log-streaming.md).
