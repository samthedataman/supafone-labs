# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Documented Supafone Labs as the developer framework behind Supafone, including
  hosted inbound/outbound agents, Supafone-managed phone numbers, built-in
  stages and tools, artifacts, and Supafone Pro watcher.
- Updated the TypeScript SDK examples to use the managed-number helpers
  `createInboundWithNumber()` and `createOutboundWithNumber()` for the default
  no-Twilio-account path.

## [0.3.0] - 2026-07-02

### Added — the open-core launch
- **`supafone_labs.stt`** — live multilingual transcription: `DeepgramLiveSTT` +
  `MultilingualCallTap` (two-track, degrade-safe, modeled on the production
  Twilio-fork consumer), nova-3 `language=multi` code-switching verified live
  (streaming `languages` tag location fixed against real frames),
  `choose_language_mode()` (multi vs pinned-mono resolution), and
  `recommended_setup(provider)` — the per-provider combination matrix enforcing
  ONE transcript source per call.
- **Supafone Labs Cloud** (`cloud/`) — the pro tier as a universal gateway: hosted
  oracle (multi-vendor model routing + aliases), hosted TTS across four engines
  under one voice namespace, hosted prerecorded STT, a live streaming STT
  websocket proxy (the tap with zero Deepgram account), key issuance + daily
  plan metering, usage API, and a Stripe checkout webhook that auto-issues and
  emails keys.
- **Pro routing in the package** — with `SUPAFONE_LABS_API_KEY` set and no
  Deepgram key, `DeepgramLiveSTT` transparently connects through the hosted
  `/v1/stt/live` proxy; BYO keys always win when present.
- **Landing page** (`landing/`) — static SaaS page with live Stripe checkout.
- `stt` extra (`pip install supafone-labs[stt]`), CI on master.

## [0.2.1] - 2026-07-02

### Changed — schemas verified against live APIs and official docs
- **Live-verified** (new `tests/test_live_providers.py`, `-m live`): Ultravox REST
  messages (adapter now accepts `MESSAGE_ROLE_*` role spellings), ElevenLabs
  Conversational AI (real session; `contextual_update` whisper accepted live),
  Cartesia Ink STT (real transcript frames round-tripped through the adapter),
  Inworld TTS (added `InworldTTSProvider` as a fourth BYO backend).
- **Vapi**: parse the real nested `{"message": {...}}` envelope, `transcriptType`
  partial/final with text in `transcript`, `tool-calls`/`toolCallList`,
  `status-update`, `end-of-call-report` (+ artifact recording); session id from
  `call.id`. Legacy flat shapes still parse.
- **Bland**: honest rewrite — parses the real end-of-call webhook
  (`transcripts[].user`, `concatenated_transcript`, `recording_url`) and live
  `webhook_events` speech lines; injection removed (Bland documents no mid-call
  control API), adapter is now tap-only.
- **GPT-Realtime**: accepts GA event names (`response.output_audio_transcript.*`,
  `conversation.item.done`) alongside beta names; caller speech now parsed from
  `conversation.item.input_audio_transcription.delta/completed`.
- **Grok**: matched to xAI's Voice Agent API — `conversation.created`, cumulative
  `conversation.item.input_audio_transcription.updated` (partial), no fictional
  agent-transcript events.
- **Deepgram Voice Agent**: documented payload fields — `UpdatePrompt{prompt}`,
  `InjectAgentMessage{message, behavior}`; parses `PromptUpdated`/`SpeakUpdated`
  and `InjectionRefused`.
- **ElevenLabs**: added current `agent_chat_response_part` streaming text and
  `agent_response_correction` (post-interruption truth); `tentative_agent_response`
  kept as legacy.
- **Pipecat**: `LLMTextFrame` streams as agent partials; injected
  `LLMMessagesAppendFrame` sets `run_llm: false` so whispers never force a turn.
- **LiveKit**: skip text-less conversation items (`AgentHandoff`).

## [0.2.0] - 2026-07-01

### Added
- **9 new provider adapters** — Retell (custom-LLM WS + webhooks), xAI Grok Realtime,
  ElevenLabs Conversational AI (`contextual_update` injection), Deepgram (Voice Agent
  `UpdatePrompt`/`InjectAgentMessage` + raw streaming-STT `Results`, tap), Pipecat
  (`LLMMessagesAppendFrame` injection), LiveKit Agents (chat-context append), Cartesia
  Ink (tap-only), Inworld (tap-only), and a configurable `GenericWebhookAdapter` —
  all registered in the facade's default set; unknown providers fall back to generic.
- **Free/Pro tiers** (`supafone_labs.tiers`): free = your own keys (or offline fakes),
  pro (`SUPAFONE_LABS_API_KEY`) = hosted oracle + hosted TTS on Supafone Labs' keys.
  `HostedLLMProvider` added; LLM registry auto-resolves hosted → Anthropic → OpenAI → fake.
- **`supafone_labs.tts`** — Supafone Labs' own TTS layer: `SupafoneLabsTTS` tier-aware front
  with a degrade chain (hosted → Deepgram Aura → Cartesia Sonic → ElevenLabs → offline
  WAV fake), `get_tts_provider()` registry, and `Supafone Labs.speak()` on the facade.
- **Test suite**: ~170 offline tests covering parse/inject/capability consistency for
  every adapter, end-to-end facade runs per provider, tier/registry resolution, and TTS;
  plus live Deepgram STT/TTS tests (`-m live`).

### Fixed
- Provider auto-detection now prefers specific hints over generic ones
  ("GrokRealtimeBot" detects as grok, not gpt_realtime).
- Bland capabilities now reflect its real mid-call prompt-patch channel.

### Added (0.1.0 groundwork)
- `adhera`: provider-agnostic voice runtime — canonical events, deterministic state
  reducer, truth/consent/watchdog/recovery policies, replay log, and adapters for
  Ultravox, Vapi, Bland, and GPT-Realtime.
- `supafone_labs`: LLM oracle (belief-state engine, directive generator, off-hot-path
  OracleSession + Adhera-compatible OracleWorkflow), prompt gradient-descent optimizer
  (TextGrad / OPRO / bootstrap-fewshot) over the Adhera replay corpus, online
  reinjection, universal `PromptProgram` framework adapters, cloud OpenAPI service, SDK,
  and the `supafone_labs.supercharge()` one-line facade.
- Provider adapters in progress: Retell, Pipecat, LiveKit Agents, xAI Grok Realtime,
  and a configurable `GenericWebhookAdapter`.

## [0.1.0] - TBD
- Initial public release.
