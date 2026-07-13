# Examples — every permutation

Each file is a minimal, complete integration for one stack. The pattern never
changes: **construct** a `Supafone Labs`, **observe** the platform's raw events,
**deliver** the compiled native action. Only the transport differs.

**Start here →** [`full_stack_twilio_ultravox.py`](full_stack_twilio_ultravox.py):
a real deployment in one file — Twilio number + Ultravox agent + Supafone Labs
supervising via an audio fork, tapping as Deepgram and whispering as Ultravox
(`inject_via="ultravox"`). Swap the provider name and the same shape supervises
Vapi/Retell/ElevenLabs.

| File | Stack | Kind | Whisper delivery |
|---|---|---|---|
| `full_stack_twilio_ultravox.py` | **Twilio + Ultravox + Supafone Labs** | full deployment | tap audio, `inject_via` the agent |
| `ultravox_end_to_end.py` | Ultravox | S2S agent | `inject_message` on the call WS |
| `vapi_webhook_server.py` | Vapi | pipeline agent | `add-message` posted to the call `controlUrl` |
| `retell_custom_llm.py` | Retell | custom-LLM WS | system message prepended to your LLM turn |
| `elevenlabs_agent.py` | ElevenLabs Agents | pipeline agent | `contextual_update` frame |
| `deepgram_voice_agent.py` | Deepgram Voice Agent | pipeline agent | `UpdatePrompt` message |
| `gpt_realtime.py` | OpenAI Realtime | S2S agent | system `conversation.item.create` |
| `pipecat_pipeline.py` | Pipecat | framework | `LLMMessagesAppendFrame` |
| `livekit_agent.py` | LiveKit Agents | framework | chat-context append |
| `twilio_sip_multilingual_tap.py` | Twilio media streams | telephony | tap + your delivery |
| `telephony_telnyx_tap.py` | Telnyx Call Control | telephony | tap + `inject_via` your agent |
| `telephony_signalwire_tap.py` | SignalWire cXML streams | telephony | tap + `inject_via` your agent |
| `custom_model_and_prompts.py` | any | — | pick model/provider, custom oracle prompts |
| `cloud_typescript.ts` | Supafone Labs Cloud | TypeScript | oracle + TTS + live STT over the hosted API |
| `create_supafone_agent.ts` | Supafone API | TypeScript | spawn a hosted Ultravox-backed Supafone agent |
| `create-basic-agent.ts` | Supafone API | TypeScript | create a general multistage intake agent |
| `create-legal-intake-agent.ts` | Supafone API | TypeScript | create a legal intake agent with routing and Supafone Pro |
| `create-medical-receptionist.ts` | Supafone API | TypeScript | create a medical receptionist with safe triage guardrails |
| `create-sales-agent-with-supafone-pro.ts` | Supafone API | TypeScript | create a speed-to-lead sales agent with Supafone Pro watcher |
| `list-voices.ts` | Supafone API | TypeScript | list Supafone-managed voices without provider keys |
| `install-widget.ts` | Supafone API | TypeScript | create a web intake agent and print the widget snippet |
| `smoke-hosted-agent.ts` | Supafone API | TypeScript | production smoke: discover capabilities, create an agent, fetch it back, and verify Supafone-managed runtime |

SIP note: Telnyx, SignalWire, Vonage, Plivo, Jambonz, FreeSWITCH/Asterisk, and
SIPREC forks all reduce to `twilio_sip_multilingual_tap.py` — fork the audio,
feed the tap.

## Production smoke test

Run this against staging or production before handing a key to a developer:

```bash
cd supafone-labs
SUPAFONE_API_KEY=sf_live_... \
SUPAFONE_API_BASE_URL=https://api.supafone.ai \
npx tsx examples/smoke-hosted-agent.ts
```

The script fails if the API cannot list capabilities, presets, or voices; if
agent creation fails; if fetching the created agent fails; if the runtime is not
`supafone_managed`; or if the web widget snippet is missing.
