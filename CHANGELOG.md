# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.8] - 2026-07-12

### Added
- Provider-neutral phone tester clients in Python and TypeScript, including
  capability discovery, authorized PSTN test starts, session polling,
  transcripts, and verdicts.
- Native Supafone and Gemini Live runtime adapters plus an executable provider
  injection contract matrix covering 14 voice runtimes.

### Fixed
- Preserved the `0.4.7` Voice Watcher default and native Ultravox BYOK
  passthrough while adding the tester APIs.
- Gemini Live control messages use a valid mid-session `user` role and retain
  availability, consent-guard, and summary-reconciliation decisions.
- Gemini Live parsing preserves every transcript emitted in a combined server
  frame instead of returning only the first event.

## [0.4.7] - 2026-07-12

### Fixed
- **Silent-injection adapter payloads** now compile each vendor's true mid-call
  "steer without speaking" primitive instead of a control that would be voiced
  back to the caller:
  - **Vapi** — Live Call Control `add-message` with `triggerResponseEnabled:false`
    (kind `control_add_message`), replacing `assistant_override`. The system
    turn lands in context silently and is not spoken or forced into a reply.
  - **OpenAI Realtime (`gpt_realtime`)** — one-shot `conversation.item.create`
    (a `system` item with no following `response.create`; kind
    `conversation_item_create`), replacing the durable `session_update`
    prompt patch. A per-turn whisper, not a standing re-steer.
  - **Ultravox** — `inject_message` payload now sends `user_text_message` with
    `urgency:"later"`, which queues the instruction without interrupting or
    voicing it (`message` kept as a back-compat alias of `text`).
  - **LiveKit** — `chat_context_append` now uses `role:"assistant"` (LiveKit's
    canonical silent-context role) rather than `system`, which a realtime model
    voices.
  - Vapi and OpenAI Realtime now report
    `supports_hidden_instruction_injection = True`.

### Added
- **Gemini Live API adapter** (`gemini`) — speech-to-speech over the Live API
  bidi websocket. Parses `serverContent` (caller `inputTranscription`, model
  `outputTranscription`, streamed `modelTurn` parts, `turnComplete`), `toolCall`
  functionCalls, and `goAway`. Silent injection is a `user`-role
  `send_client_content` turn with `turnComplete:false` (Gemini content roles are
  only user/model). Registered in the default adapter set and exported from
  `supafone_labs.runtime.adapters`.

## [0.4.6] - 2026-07-11

### Docs
- Accurate silent-injection support matrix: 10 frameworks (Ultravox, OpenAI
  Realtime, Grok, Gemini Live, ElevenLabs, Inworld, Vapi, Retell, Deepgram,
  LiveKit) with their exact per-framework primitive and injection mode (A =
  native silent event, B = own the LLM). Bland is unsupported by vendor design
  (closed live-call API, no mid-call inject channel, no custom-LLM); Cartesia
  and Pipecat are n/a (a TTS voice and a DIY framework, not conversational
  agents). New `gitbook/framework-support.md` page (added to `SUMMARY.md`),
  cross-linked from the Voice Watcher and provider-agnostic pages; README and
  TS README gain a matching "Supported frameworks" section. Honest caveat added
  throughout: injection is possible for all 10, but managed delivery is wired
  end-to-end only for Ultravox today.

### Added
- **Native (BYOK) Ultravox runtime**: connect your own Ultravox key via
  `byok.ultravox` on agent create or `PUT /api/v1/labs/runtime`. Agents then
  RUN and are MONITORED (transcript, summary, live supervision) on your own
  Ultravox account instead of the Supafone platform key. Absent a key the
  managed platform runtime is used exactly as before.
  - `GET /api/v1/labs/runtime` reports `{managed, byok_connected, base_url}`;
    `PUT /api/v1/labs/runtime` connects/updates the key (masked; never echoed).
  - `capabilities().runtimes.byok == ["ultravox"]`.
- **`voice_watcher` (`voiceWatcher` in TS) client flag** — one switch to run
  agents under the Voice Watcher framework (supervision + QA + scoring); default
  on. Injected into `labs.agents.create*` payloads when the caller didn't set it
  (explicit values are preserved). The deprecated `labs=` client arg still works.

## [0.4.5] - 2026-07-11

### Added
- **`/api/v1/labs/*` provisioning API is live in the product backend**
  (`api.supafone.ai`). The routes the SDK has always called now exist and run
  the real product internals — they are no longer 404:
  - `POST/GET/DELETE /api/v1/labs/agents[/{agent_key}]` — translate a labs
    agent payload into a real product agent (managed **Ultravox** runtime),
    saved via the product store.
  - `POST /api/v1/labs/phone-numbers[/search|/{id}/assign|/unassign|/release]`
    — the real Twilio number lifecycle (search → buy → attach → release),
    reusing the existing phone flow.
  - `GET/PUT /api/v1/labs/telephony` — configure BYOK telephony
    (Twilio / Telnyx / Plivo / SIP); credentials are stored encrypted and the
    account's outbound dialing is pointed at the chosen carrier.
  - `GET /api/v1/labs/capabilities` — the provisioning contract, supported
    runtimes/providers, industry presets, and the live voice catalog.
- `agents.create_inbound_with_number` / `create_outbound_with_number` now work
  end to end against the hosted API (create + provision + assign in one call).

### Notes
- The managed runtime is **Ultravox**. Non-Ultravox agent stacks
  (`byok.agentProvider` = Vapi / Retell / Bland / LiveKit / Pipecat) are a
  later phase and return a clear `400` — they are not silently faked.

## [0.4.4] - 2026-07-10

### Added
- **One-key auth** — a single `sl_` Labs key now authenticates on **both**
  APIs: the product API (`api.supafone.ai`) accepts it anywhere an account JWT
  works by introspecting the key against Labs Cloud and mapping the key's
  owner email to the app.supafone.ai account (fail-closed 401 on anything
  doubtful; short in-process cache). Both SDK constructors cross-fill every
  credential lane from a lone `sl_` credential, and the MCP server runs end
  to end from `SUPAFONE_TOKEN=sl_live_...`.
- `GET /v1/keys/introspect` on Labs Cloud — returns `{email, plan, active}`
  for the presented key; 401 for unknown or deactivated keys.

## [0.4.3] - 2026-07-10

### Added
- **Brand scan** — `POST /api/v1/agents/brand-scan` (+ SDK
  `scan_brand`/`scanBrand`, MCP `scan_brand`): business name, brand colors,
  logo, favicon, Open Graph metadata, page images, and key same-domain pages
  from any URL.
- **Intake-form generation** — `POST /api/v1/agents/generate-intake` and
  `POST /api/v1/agents/{agent_id}/generate-intake` (+ SDK
  `generate_intake_form`/`generateIntakeForm`, MCP `generate_intake_form`).
- **Campaigns as code** — campaign YAML/JSON configs gain `branding:` (scan a
  URL on apply and/or explicit colors/logo/favicon) and `intake_form:`
  (LLM-generate from a description, or an explicit config) blocks;
  `POST /api/v1/campaigns/config/{validate,apply,generate}` and
  `GET /api/v1/campaigns/{id}/config`; SDK
  `campaigns.validate_config/apply_config/export_config/generate_config`
  (TS camelCase); MCP `generate_campaign_config`, `apply_campaign_config`
  (validates first, `filePath` support), `export_campaign_config`.

## [0.4.2] - 2026-07-10

### Added
- **E-sign fully code-drivable** — upload a signing PDF and auto-place
  signature fields from code: SDK
  `campaigns.upload_signing_document/detect_signature_fields/set_signature_fields`
  (TS `uploadSigningDocument`/`detectSignatureFields`/`setSignatureFields`)
  plus the matching MCP tools, so the whole signature chase runs from prose:
  upload the retainer, apply the detected coordinates, add leads, launch.

## [0.4.1] - 2026-07-10

### Added
- **Builder copilot wizard** — `POST /v1/builder/wizard` extracts structured
  agent-builder fields from a free-form conversation; the Labs builder gains a
  Claude-style conversational copilot panel that drives the real form.
- **Auto QA suites + SSR grading in the cloud API** — `POST /v1/qa/suite`
  generates and runs an adversarial suite in one call; SSR five-level nominal
  grading (`SSR_LEVELS`) with deterministic score mapping.
- **Python SDK QA + post-call-analysis parity** — `client.Supafone` gains
  `post_call_analysis=True` (auto-classifying `report_call()`),
  `classify_call()`, `labs_login()`, and a `qa` namespace
  (`qa.generate/run/suite/history`) matching the TypeScript SDK 1:1; new
  tests in `tests/test_qa_client.py`.
- **Campaigns as SDK packages** — `campaigns` namespace in both SDKs
  (create/get/list/start/pause/report) with live monitoring; MCP campaign
  tools + `place_call` against the main Supafone API.
- **New paper: "Grading the Call"** (`paper/voice-qa.tex` + compiled PDF) —
  objective-derived adversarial suites, SSR nominal-scale judging with
  deterministic score distributions, supervision-lift A/B, ground-truth
  blending, and the OPRO loop, situated against the 2025–2026 voice-QA
  landscape with an 18-entry bibliography.
- **Developer-facing docs rewrite** — the GitBook overview now opens with the
  developer pain points solved (numbers, TTS/STT, RAG, tool calls,
  self-healing, call classification, QA in 5 lines of code), the
  every-framework-one-framework argument, the self-healing agent-swarm /
  call-center-infrastructure vision, the one-key-vs-two-surfaces explanation,
  and 🐍/🟦 package icons + GitHub / labs.supafone.ai links; the QA landscape
  page is written developer-first (quick start, tool comparison, honest
  roadmap, enterprise checklist) and mirrored to the landing GitBook; new
  "Why Supafone" page.
- **Automatic post-call analysis** — `SupafoneLabs(post_call_analysis=True)`
  (Python) and `new Supafone({ postCallAnalysis: true })` (TypeScript): every
  finished call is classified against the agent's objective via
  `POST /v1/calls/classify`, generating labels — achieved/missed,
  per-criterion verdicts, failure reasons, blended objective value — and
  filing the enriched report for the optimizer. Results surface on
  `brain.analyses` / `brain.last_analysis` / `brain.analysis(session_id)`
  (Python) and on `reportCall()`'s `analysis` field (TS). Falls back to the
  plain zero-billed report on any failure. New telemetry helper
  `classify_call_report()`; new TS method `classifyCall()`.
- **TS SDK QA parity** — `qa.generate()` (`POST /v1/qa/generate`, adversarial
  scenarios from the agent's own prompt) and `qa.suite()`
  (`POST /v1/qa/suite`, one-call auto suite with pass/fail assertions + SSR
  grades), with typed `QAScenario`, `SSRGrade`, and `QASuiteResult` shapes.
- **Voice-Agent QA Landscape** docs page (`gitbook/voice-qa-landscape.md`,
  mirrored to the landing GitBook): 2026 competitive teardown of Hamming,
  Coval, Roark, Cekura, Bluejay, platform-native testing (Bland/Retell/Vapi),
  OSS frameworks (promptfoo/DeepEval/Braintrust/voicetest), and academic
  benchmarks (τ²-bench, VoiceBench) — plus differentiators, ranked gaps, the
  feature roadmap with API shapes, and console visualization/packaging specs.

## [0.3.2] - 2026-07-09

### Added
- SSR grading: `/v1/builder/finish` grades on a five-level nominal scale
  ("the agent did {poorly|ok|good|great|perfectly} at achieving the
  objective"), mapped deterministically to canonical scores and 10-bucket
  distributions via a LangGraph flow (`cloud/ssr_grading.py`).
- `GET /v1/objective/distribution` — aggregate SSR labels into a real score
  distribution; surfaced in the console Reporting section.
- TS SDK `optimizer.distribution()` and Python `Supafone.objective_distribution()`.
- The optimizer improve step now weights directive changes toward moving
  calls out of the lowest SSR levels first.

## [0.3.1] - 2026-07-08

### Added
- Hosted agent builder/test chat, log streaming, tester media WS, tiered
  Stripe grants, admin/billing endpoints, and the unscoped `supafone-labs`
  package rename across SDKs and docs.

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
