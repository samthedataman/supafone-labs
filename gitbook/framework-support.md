# Framework Coverage

Supafone Labs exposes **fourteen audited runtime integrations**. Every adapter
converts provider-specific events into one canonical call state. When a runtime
has a supported control channel, the same abstract Watcher directive is
compiled back into that runtime's native message or developer-owned context.

This page distinguishes five different claims that should never be conflated:

| Support class | Meaning |
| --- | --- |
| Managed native control | Supafone owns the delivery path and sends the control through the managed call runtime |
| Native control | The provider exposes a documented live control accepted by its active session |
| Developer-owned context | The application owns the LLM or framework context and applies the compiled directive locally |
| Observation only | Supafone can normalize events, supervise, score, and report, but the provider exposes no universal live prompt-control channel |
| Explicit host hook | The component exposes an event transport, but the developer's agent must decide how to apply it |

## Runtime matrix

| Runtime | Support class | Watcher delivery | Acceptance criterion |
| --- | --- | --- | --- |
| <a id="provider-supafone"></a>Supafone Agent Factory | Managed native control | Ultravox `user_text_message` with `urgency=later` | Managed call accepts the data message |
| <a id="provider-ultravox"></a>Ultravox | Native control | Deferred `user_text_message` | Send Data Message returns HTTP 204 |
| <a id="provider-vapi"></a>Vapi | Native control | System `add-message` through the live call `controlUrl` | Control request succeeds and the message enters live context |
| <a id="provider-retell"></a>Retell | Developer-owned context | System entry in the custom-LLM WebSocket context | Entry exists before the next response is emitted |
| <a id="provider-bland"></a>Bland | Observation only | No universal prompt-injection action | Events normalize without emitting an unsupported action |
| <a id="provider-gpt_realtime"></a>OpenAI Realtime | Native control | System `conversation.item.create` | Item-created or item-done event arrives without provider error |
| <a id="provider-grok"></a>Grok Voice Agent | Native control | `response.create.instructions` | Provider emits `response.created` followed by completion or an error |
| <a id="provider-gemini_live"></a>Gemini Live | Native control | `clientContent` user turn; system role is invalid mid-session | Subsequent server content reflects the accepted update |
| <a id="provider-elevenlabs"></a>ElevenLabs Agents | Native control | `contextual_update` | Socket remains healthy and the next turn completes |
| <a id="provider-deepgram"></a>Deepgram Voice Agent | Native control | `UpdatePrompt` | Provider emits `PromptUpdated` |
| <a id="provider-livekit"></a>LiveKit Agents | Developer-owned context | `ChatContext.add_message` followed by `update_chat_ctx` | Persisted context contains the system entry |
| <a id="provider-pipecat"></a>Pipecat | Developer-owned context | `LLMMessagesAppendFrame` with `run_llm=false` | Context aggregator retains the developer message |
| <a id="provider-cartesia"></a>Cartesia Line | Explicit host hook | Custom metadata event; no default prompt action | Host agent explicitly handles the event |
| <a id="provider-inworld"></a>Inworld Realtime | Native control | System `conversation.item.create` | Item-added or item-done event arrives without provider error |

`GenericWebhookAdapter` is the configurable extension path for proprietary
systems. It is deliberately not counted as one of the fourteen audited
runtimes.

## What the package covers around the runtime

The voice runtime is one layer. Supafone Labs also normalizes the infrastructure
developers otherwise assemble around it.

| Layer | Supported surfaces | Pain removed |
| --- | --- | --- |
| Agent runtimes | The fourteen integrations above plus generic webhooks | Rewriting supervision and state for every provider |
| Telephony | Supafone-managed, Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks | Separate number, carrier, webhook, and media-stream implementations |
| TTS | Supafone hosted, Cartesia, Inworld, ElevenLabs, Deepgram Aura, custom `TTSProvider`, deterministic fake | Provider-specific synthesis APIs and incompatible voice metadata |
| STT | Deepgram Nova-3 live multilingual tap, provider-native transcripts, Twilio/raw audio taps | Duplicate transcripts, missing language authority, and provider-specific event parsing |
| Supervisor LLM | Supafone hosted, Anthropic, OpenAI, xAI, custom `LLMProvider`, deterministic fake | Hard-coding the supervisor to one model vendor |
| Prompt programs | DSPy, LangChain, raw templates, provider-native message arrays, `PromptProgram` | Rebuilding optimization and prompt conversion per framework |
| Developer access | Python, TypeScript, Node, React/browser, REST, WebSocket, MCP | Maintaining separate product APIs for every application surface |

## Managed delivery versus adapter support

The fourteen-row matrix describes audited event parsing and action compilation.
It does **not** mean Supafone hosts every provider account automatically.

- Supafone's default managed Agent Factory path currently uses its managed
  Ultravox transport and managed provider accounts.
- BYOK deployments can use the provider-native or developer-owned controls
  listed above.
- Bland remains useful for observation, post-call grading, QA, and telemetry,
  but its documented live API does not expose a universal hidden-instruction
  channel.
- Cartesia Line requires an explicit handler in the host agent. A custom event
  is transport, not proof that the agent applied the instruction.
- Unsupported or uncertain capability always degrades to no action. Supafone
  does not invent a provider control.

## Transcript and language authority

Supafone selects exactly one transcript authority per call:

- Provider transcript for a supported monolingual stream.
- Deepgram live tap when multilingual language authority is required and raw
  audio is available.
- Oracle heuristics only where a provider supplies transcript text but no
  language tags and no raw-audio tap is available.

This prevents duplicate ingestion and conflicting language decisions. See
[Live language and voice routing](live-language-voice-routing.md) for the
opt-in hosted-agent behavior.

## Release gates

The public release verifies framework support at three levels:

1. `tests/test_provider_injection_e2e.py` runs all fourteen adapters from a
   provider event through canonical state, Watcher decision, and exact action.
2. `tests/test_live_injection_contracts.py` performs credentialed acceptance
   probes where the vendor exposes a live test path. Missing credentials are
   skips, never passes.
3. `tests/test_documentation_framework_matrix.py` requires this page to contain
   every runtime from `provider_contracts.py` and rejects duplicate or stale
   matrix entries.

The provider contract registry includes the primary vendor documentation,
acceptance behavior, verification date, and probe type for every row. The
technical reference is also available in
[Providers and frameworks](https://github.com/samthedataman/supafone-labs/blob/main/docs/providers.md).
