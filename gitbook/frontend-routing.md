# Frontend Routing

This page is for the Labs frontend docs and builder navigation. It explains how
the static frontend should route users through the developer experience.

## Primary Routes

| Route | Purpose |
| --- | --- |
| `/` | Product overview and entry points |
| `/docs.html` | Native docs index or GitBook handoff |
| `/builder.html` | Agent Factory and provider-agnostic builder |
| `/console.html` | Account, usage, logs, keys |
| `/tester.html` | Oracle/TTS/STT playground |
| `/get-key.html` | Labs Cloud key signup |
| `/pricing.html` | Pricing and credits |

GitBook docs should mirror those routes with pages for quickstart, Agent
Factory, provider framework, BYOK, voices, logs, MCP, and E2E testing.

## Builder First Screen

The first screen should answer one question: "How do I create a working agent
with one key?"

Required above-the-fold controls:

1. Supafone API key.
2. Inbound/outbound selector.
3. Agent name and prompt.
4. Voice provider and voice preview.
5. Labs on/off with managed/BYOK mode.
6. Number strategy.
7. Create agent.
8. Export TypeScript/Python.
9. Log stream.

Advanced credentials should be split into three drawers:

| Drawer | Examples |
| --- | --- |
| Agent/provider stack | Ultravox, Retell, Vapi, Bland, LiveKit, Pipecat, GPT Realtime, Grok |
| Telephony | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks |
| TTS | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS |

## Export Panel

The builder should export:

- TypeScript SDK,
- Python SDK,
- REST/curl,
- JSON payload.

The exported config should be the same payload the builder sends. That makes
the UI a code generator instead of a demo.

## Logs Panel

The builder should connect to:

```text
GET /v1/logs
GET /v1/logs/stream
```

Show endpoint, provider, model, voice, duration, billed seconds, and detail.
Provide a raw JSON drawer per row.

## Voice Preview Panel

Use:

```text
GET  /v1/voices
POST /v1/tts
```

The preview should be available before provisioning the final agent. If the
selected engine is not configured or the key has no balance, show the API error
directly and keep the rest of the builder usable.
