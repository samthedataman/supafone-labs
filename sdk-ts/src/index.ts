/**
 * Supafone Labs — the agent framework behind Supafone.
 *
 * A dependency-free TypeScript client for creating hosted Supafone agents
 * through the Supafone API, including managed phone numbers, voices, stages,
 * tools, recordings, transcripts, widgets, and Supafone Pro watcher. It also
 * includes the Labs cloud sidecar oracle, hosted TTS/STT, live multilingual
 * transcription, telemetry, agent builder, and objective-driven optimizer.
 *
 * Works in Node 18+ (native fetch/WebSocket) and the browser.
 *
 *   npm i supafone-labs
 *
 *   import { Supafone } from "supafone-labs";
 *   const supafone = new Supafone({ apiKey: process.env.SUPAFONE_API_KEY! });
 *   const agent = await supafone.labs.agents.createInboundWithNumber({
 *     agentKey: "northline-intake",
 *     name: "Northline intake",
 *     number: { search: { areaCode: "415" } },
 *   });
 */

export interface SupafoneLabsOptions {
  /** Your key from https://labs.supafone.ai/get-key.html */
  apiKey?: string;
  /** Override the gateway (default: the hosted cloud). */
  baseUrl?: string;
  /** Supafone app/API key for hosted agent provisioning. Defaults to apiKey. */
  supafoneApiKey?: string;
  /** Override the Supafone API used by supafone.labs.* (default: https://api.supafone.ai). */
  supafoneApiBaseUrl?: string;
  /** Per-request timeout in ms (default 30_000). */
  timeoutMs?: number;
  /** Optional pre-obtained session token (else use login()). */
  sessionToken?: string;
  /**
   * Account (app.supafone.ai) auth — powers campaigns + real calls. Pass a
   * JWT (or an `sl_` Labs key — one key works on both APIs) directly, or
   * accountEmail + accountPassword and the client logs in lazily (and
   * re-logs-in once when the token expires). With account auth present,
   * apiKey becomes optional; an `sl_` apiKey also fills this lane by itself.
   */
  accountToken?: string;
  accountEmail?: string;
  accountPassword?: string;
  /** Portal base for listen/monitor links (default https://app.supafone.ai). */
  appUrl?: string;
  /**
   * Automatic post-call analysis. When true, reportCall() with a transcript
   * (or structured messages) first classifies the finished call against the
   * agent's objective — generating labels (achieved/missed, per-criterion
   * verdicts, failure reasons) — and files the enriched report server-side.
   * Billed one oracle call per analyzed call; reports without a transcript
   * fall back to the plain zero-billed report.
   */
  postCallAnalysis?: boolean;
  /**
   * Run provisioned agents under Supafone's Voice Watcher framework — live
   * supervision, QA, and call scoring (default true). Set false for a raw
   * agent with no watcher. `voice_watcher` (snake) and the deprecated `labs`
   * are accepted aliases, resolved voiceWatcher > voice_watcher > labs > true.
   */
  voiceWatcher?: boolean;
  voice_watcher?: boolean;
  /** @deprecated alias for voiceWatcher. */
  labs?: boolean;
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface OracleRequest {
  messages: ChatMessage[];
  /** Any claude-* / gpt-* / grok-* id, or the alias "supafone-labs-oracle". */
  model?: string;
  maxTokens?: number;
  temperature?: number;
}

export interface OracleResult {
  text: string;
  model: string;
  usage?: Record<string, number>;
}

export interface WhisperOptions {
  model?: string;
  /** Extra operator rules folded into the coaching system prompt. */
  guardrails?: string;
  maxTokens?: number;
  temperature?: number;
}

export interface Balance {
  plan: string;
  seconds_remaining: number;
  minutes_remaining: number;
  top_up?: { subscribe_monthly?: string; buy_credit_pack?: string; note?: string };
}

export interface UsageToday {
  plan: string;
  day: string;
  usage: Record<string, { used: number; cap: number }>;
}

export interface LabsLogEntry {
  id: number;
  at: string;
  endpoint: string;
  seconds_billed: number;
  duration_ms: number;
  detail: string;
  meta: Record<string, unknown>;
}

export interface StreamLogsOptions {
  limit?: number;
  afterId?: number;
  pollMs?: number;
  snapshot?: boolean;
  signal?: AbortSignal;
}

export type LabsAgentType = "phone" | "web" | "campaign";
export type LabsAgentStyle = "inbound" | "outbound";
export type LabsRuntimeMode = "multi_stage" | "single_stage";
export type LabsTelephonyMode = "supafone_managed" | "byok";
export type LabsTelephonyProvider =
  | "supafone"
  | "twilio"
  | "telnyx"
  | "plivo"
  | "signalwire"
  | "sip"
  | "custom_sip"
  | "custom"
  | string;
export type LabsNumberStrategy = "default_pool" | "dedicated" | "premium" | "byok" | string;

export interface LabsCallStage {
  key?: string;
  id?: string;
  name: string;
  goal?: string;
  instructions?: string;
  exitCriteria?: string[];
  exit_criteria?: string[];
  tools?: string[];
  metadata?: Record<string, unknown>;
}

export interface LabsVoiceSelection {
  provider?: string;
  voiceId?: string;
  voice_id?: string;
  model?: string;
}

export interface LabsProviderKeys {
  /** Agent runtime/platform providers. */
  ultravox?: string;
  ultravoxApiKey?: string;
  ultravox_api_key?: string;
  retell?: string;
  retellApiKey?: string;
  retell_api_key?: string;
  vapi?: string;
  vapiApiKey?: string;
  vapi_api_key?: string;
  bland?: string;
  blandApiKey?: string;
  bland_api_key?: string;
  livekit?: string;
  livekitApiKey?: string;
  livekit_api_key?: string;
  livekitApiSecret?: string;
  livekit_api_secret?: string;
  pipecat?: string;
  pipecatApiKey?: string;
  pipecat_api_key?: string;
  /** Telephony/carrier providers. */
  twilio?: string;
  twilioAccountSid?: string;
  twilio_account_sid?: string;
  twilioAuthToken?: string;
  twilio_auth_token?: string;
  twilioApiKeySid?: string;
  twilio_api_key_sid?: string;
  twilioApiKeySecret?: string;
  twilio_api_key_secret?: string;
  telnyx?: string;
  telnyxApiKey?: string;
  telnyx_api_key?: string;
  plivo?: string;
  plivoAuthId?: string;
  plivo_auth_id?: string;
  plivoAuthToken?: string;
  plivo_auth_token?: string;
  signalwire?: string;
  signalwireApiToken?: string;
  signalwire_api_token?: string;
  signalwireProjectId?: string;
  signalwire_project_id?: string;
  /** TTS providers. */
  elevenlabs?: string;
  elevenlabsApiKey?: string;
  elevenlabs_api_key?: string;
  cartesia?: string;
  cartesiaApiKey?: string;
  cartesia_api_key?: string;
  inworld?: string;
  inworldApiKey?: string;
  inworld_api_key?: string;
  deepgram?: string;
  deepgramApiKey?: string;
  deepgram_api_key?: string;
  /** Brain/STT providers used by Labs watcher or customer BYOK stacks. */
  anthropic?: string;
  anthropicApiKey?: string;
  anthropic_api_key?: string;
  openai?: string;
  openaiApiKey?: string;
  openai_api_key?: string;
  xai?: string;
  xaiApiKey?: string;
  xai_api_key?: string;
  [extra: string]: unknown;
}

export interface LabsCustomSipConfig {
  sipTrunkUri?: string;
  sip_trunk_uri?: string;
  trunkUri?: string;
  trunk_uri?: string;
  sipHost?: string;
  sip_host?: string;
  fromNumber?: string;
  from_number?: string;
  username?: string;
  password?: string;
  transport?: string;
  headers?: Record<string, string>;
  codecs?: string[];
  dtmfMode?: string;
  dtmf_mode?: string;
  metadata?: Record<string, unknown>;
  [extra: string]: unknown;
}

export interface LabsProviderByokConfig {
  provider?: string;
  apiKey?: string;
  api_key?: string;
  credentials?: Record<string, unknown>;
  settings?: Record<string, unknown>;
  model?: string;
  voiceId?: string;
  voice_id?: string;
  [extra: string]: unknown;
}

export interface LabsByokConfig {
  providerKeys?: LabsProviderKeys;
  provider_keys?: LabsProviderKeys;
  agentProvider?: LabsProviderByokConfig;
  agent_provider?: LabsProviderByokConfig;
  runtime?: LabsProviderByokConfig;
  telephony?: LabsTelephonyConfig;
  tts?: LabsProviderByokConfig;
  stt?: LabsProviderByokConfig;
  llm?: LabsProviderByokConfig;
  customSip?: LabsCustomSipConfig;
  custom_sip?: LabsCustomSipConfig;
  sip?: LabsCustomSipConfig;
  [extra: string]: unknown;
}

export interface LabsTelephonyCredentials {
  accountSid?: string;
  account_sid?: string;
  authToken?: string;
  auth_token?: string;
  apiKey?: string;
  api_key?: string;
  apiSecret?: string;
  api_secret?: string;
  authId?: string;
  auth_id?: string;
  connectionId?: string;
  connection_id?: string;
  telnyxConnectionId?: string;
  telnyx_connection_id?: string;
  signalwireSpaceUrl?: string;
  signalwire_space_url?: string;
  projectId?: string;
  project_id?: string;
  applicationId?: string;
  application_id?: string;
  trunkId?: string;
  trunk_id?: string;
  endpointId?: string;
  endpoint_id?: string;
  token?: string;
  secret?: string;
  fromNumber?: string;
  from_number?: string;
  sipTrunkUri?: string;
  sip_trunk_uri?: string;
  sipHost?: string;
  sip_host?: string;
  username?: string;
  password?: string;
  webhookSecret?: string;
  webhook_secret?: string;
  customSip?: LabsCustomSipConfig;
  custom_sip?: LabsCustomSipConfig;
  [extra: string]: unknown;
}

export interface LabsTelephonyConfig {
  agencyId?: string;
  agency_id?: string;
  /** Default is Supafone-managed; developers do not need Twilio for this path. */
  mode?: LabsTelephonyMode;
  provider?: LabsTelephonyProvider;
  /** default_pool reuses idle Supafone numbers; dedicated/premium reserve a number-month. */
  numberStrategy?: LabsNumberStrategy;
  number_strategy?: LabsNumberStrategy;
  numberPool?: string;
  number_pool?: string;
  numberId?: string;
  number_id?: string;
  premium?: boolean;
  label?: string;
  credentials?: LabsTelephonyCredentials;
  providerSettings?: Record<string, unknown>;
  provider_settings?: Record<string, unknown>;
  customSip?: LabsCustomSipConfig;
  custom_sip?: LabsCustomSipConfig;
  metadata?: Record<string, unknown>;
  [extra: string]: unknown;
}

export interface LabsToolsConfig {
  callRouting?: boolean;
  call_routing?: boolean;
  scheduling?: boolean;
  sms?: boolean;
  email?: boolean;
  intakeForms?: boolean;
  intake_forms?: boolean;
  firmKnowledge?: boolean;
  firm_knowledge?: boolean;
  existingClientLookup?: boolean;
  existing_client_lookup?: boolean;
  voicemail?: boolean;
  emergencyEscalation?: boolean;
  emergency_escalation?: boolean;
  customTools?: Array<Record<string, unknown>>;
  custom_tools?: Array<Record<string, unknown>>;
}

export interface LabsRecordingConfig {
  enabled?: boolean;
  recordAudio?: boolean;
  record_audio?: boolean;
  consentRequired?: boolean;
  consent_required?: boolean;
  announcement?: string;
  retentionDays?: number;
  retention_days?: number;
  storage?: "supafone_managed" | "byok" | string;
  redactPii?: boolean;
  redact_pii?: boolean;
  metadata?: Record<string, unknown>;
}

export interface LabsTranscriptionConfig {
  enabled?: boolean;
  provider?: string;
  model?: string;
  language?: string;
  redactPii?: boolean;
  redact_pii?: boolean;
  diarization?: boolean;
  timestamps?: boolean;
  metadata?: Record<string, unknown>;
}

export interface LabsArtifactsConfig {
  recordings?: boolean;
  transcripts?: boolean;
  summaries?: boolean;
  qaReports?: boolean;
  qa_reports?: boolean;
  logs?: boolean;
  webhooks?: boolean;
  retentionDays?: number;
  retention_days?: number;
  metadata?: Record<string, unknown>;
}

export interface LabsWatcherConfig {
  enabled?: boolean;
  voiceWatcher?: boolean;
  voice_watcher?: boolean;
  apiKey?: string;
  api_key?: string;
  model?: string;
  mode?: "supafone_managed" | "byok" | string;
  managedInfrastructure?: boolean;
  managed_infrastructure?: boolean;
  stt?: Record<string, unknown>;
  llm?: Record<string, unknown>;
  tts?: Record<string, unknown>;
  providerKeys?: Record<string, unknown>;
  provider_keys?: Record<string, unknown>;
  label?: string;
}

export interface LabsUltravoxRuntime {
  model?: string;
  temperature?: number;
  medium?: Record<string, unknown>;
  vadSettings?: Record<string, unknown>;
  vad_settings?: Record<string, unknown>;
  speakerFirst?: boolean;
  speaker_first?: boolean;
  firstSpeaker?: string;
  first_speaker?: string;
  firstSpeakerSettings?: Record<string, unknown>;
  first_speaker_settings?: Record<string, unknown>;
  selectedTools?: Array<Record<string, unknown>>;
  selected_tools?: Array<Record<string, unknown>>;
  initialMessages?: Array<Record<string, unknown>>;
  initial_messages?: Array<Record<string, unknown>>;
  initialState?: Record<string, unknown>;
  initial_state?: Record<string, unknown>;
  initialOutputMedium?: string;
  initial_output_medium?: string;
  joinTimeout?: string;
  join_timeout?: string;
  maxDuration?: string;
  max_duration?: string;
  maxDurationSeconds?: number;
  max_duration_seconds?: number;
  timeExceededMessage?: string;
  time_exceeded_message?: string;
  inactivityMessages?: Array<Record<string, unknown>>;
  inactivity_messages?: Array<Record<string, unknown>>;
  dataConnection?: Record<string, unknown>;
  data_connection?: Record<string, unknown>;
  callbacks?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  experimentalSettings?: Record<string, unknown>;
  experimental_settings?: Record<string, unknown>;
  voiceOverrides?: Record<string, unknown>;
  voice_overrides?: Record<string, unknown>;
  retentionPolicy?: string;
  retention_policy?: string;
  callTemplate?: Record<string, unknown>;
  call_template?: Record<string, unknown>;
  customSip?: LabsCustomSipConfig;
  custom_sip?: LabsCustomSipConfig;
  sip?: LabsCustomSipConfig;
  [extra: string]: unknown;
}

export interface CreateLabsAgentRequest {
  agencyId?: string;
  agency_id?: string;
  agentKey?: string;
  agent_key?: string;
  agentType?: LabsAgentType;
  agent_type?: LabsAgentType;
  /** inbound = receptionist/intake, outbound = sales/speed-to-lead/campaign. */
  style?: LabsAgentStyle;
  agentStyle?: LabsAgentStyle;
  agent_style?: LabsAgentStyle;
  name: string;
  assistantName?: string;
  assistant_name?: string;
  businessName?: string;
  business_name?: string;
  industry?: string;
  websiteUrl?: string;
  website_url?: string;
  phoneNumber?: string;
  phone_number?: string;
  numberStrategy?: LabsNumberStrategy;
  number_strategy?: LabsNumberStrategy;
  numberPool?: string;
  number_pool?: string;
  premium?: boolean;
  direction?: string;
  presetKey?: string;
  preset_key?: string;
  runtimeMode?: LabsRuntimeMode;
  runtime_mode?: LabsRuntimeMode;
  /** Default true. When true, the SDK creates sensible call stages from prompt metadata. */
  callStages?: boolean | LabsCallStage[];
  call_stages?: boolean | LabsCallStage[];
  stages?: LabsCallStage[];
  autoCallStages?: boolean;
  auto_call_stages?: boolean;
  goal?: string;
  greeting?: string;
  systemPrompt?: string;
  system_prompt?: string;
  language?: string;
  voice?: LabsVoiceSelection;
  providerKeys?: LabsProviderKeys;
  provider_keys?: LabsProviderKeys;
  byok?: LabsProviderKeys | LabsByokConfig;
  telephony?: LabsTelephonyConfig;
  customSip?: LabsCustomSipConfig;
  custom_sip?: LabsCustomSipConfig;
  sip?: LabsCustomSipConfig;
  recording?: LabsRecordingConfig;
  transcription?: LabsTranscriptionConfig;
  artifacts?: LabsArtifactsConfig;
  compliance?: Record<string, unknown>;
  tools?: LabsToolsConfig;
  labs?: LabsWatcherConfig;
  ultravox?: LabsUltravoxRuntime;
  voiceWatcher?: boolean;
  voice_watcher?: boolean;
  voiceWatcherModel?: string;
  voice_watcher_model?: string;
  metadata?: Record<string, unknown>;
}

export interface ListLabsAgentsOptions {
  agencyId?: string;
  agentType?: LabsAgentType;
  style?: LabsAgentStyle;
}

export interface GetLabsAgentOptions extends ListLabsAgentsOptions {}

export interface DeleteLabsAgentOptions {
  agencyId?: string;
  agency_id?: string;
  releaseNumbers?: boolean;
  release_numbers?: boolean;
}

export interface DeleteLabsAgentResponse {
  success?: boolean;
  deleted?: boolean;
  agent_key?: string;
  released_numbers?: unknown[];
  [extra: string]: unknown;
}

export interface LabsCapabilitiesResponse {
  product: string;
  api_namespace: string;
  compatibility_namespace?: string;
  default_agent_contract: Record<string, unknown>;
  capabilities: Array<Record<string, unknown>>;
  recommended_next_api_additions?: Array<Record<string, unknown>>;
  [extra: string]: unknown;
}

export interface LabsPresetListResponse {
  default_preset_key: string;
  router_policies?: Record<string, string>;
  presets: Array<Record<string, unknown>>;
}

export interface LabsToolListResponse {
  tools: Array<Record<string, unknown>>;
}

export interface LabsVoiceListOptions {
  provider?: string;
}

export interface LabsVoiceListResponse {
  voices: Array<Record<string, unknown>>;
  total: number;
  providers: Array<Record<string, unknown>>;
  provider_accounts?: Record<string, unknown>;
  errors?: Record<string, string>;
}

export interface LabsCallListOptions {
  agencyId?: string;
  agentKey?: string;
  agent_key?: string;
  limit?: number;
}

export interface LabsCallArtifact {
  id?: string;
  call_id?: string;
  agent_key?: string;
  status?: string;
  started_at?: string;
  duration_seconds?: number;
  recording_url?: string;
  transcript_url?: string;
  [extra: string]: unknown;
}

export interface LabsCallListResponse {
  calls: LabsCallArtifact[];
  [extra: string]: unknown;
}

export interface LabsRecordingListOptions extends LabsCallListOptions {
  callId?: string;
  call_id?: string;
}

export interface LabsRecordingListResponse {
  recordings: Array<Record<string, unknown>>;
  [extra: string]: unknown;
}

export interface LabsTranscriptListOptions extends LabsCallListOptions {
  callId?: string;
  call_id?: string;
}

export interface LabsTranscriptListResponse {
  transcripts: Array<Record<string, unknown>>;
  [extra: string]: unknown;
}

export interface LabsPhoneNumberSearchOptions {
  agencyId?: string;
  agency_id?: string;
  numberPool?: string;
  number_pool?: string;
  numberStrategy?: LabsNumberStrategy;
  number_strategy?: LabsNumberStrategy;
  countryCode?: string;
  country_code?: string;
  areaCode?: string;
  area_code?: string;
  postalCode?: string;
  postal_code?: string;
  zipCode?: string;
  zip_code?: string;
  contains?: string;
  numberType?: "local" | "toll_free" | "mobile" | string;
  number_type?: string;
  limit?: number;
  capabilities?: string[];
}

export interface LabsPhoneNumberOption {
  phone_number: string;
  number_type?: string;
  region?: string;
  locality?: string;
  monthly_cost?: number;
  setup_cost?: number;
  capabilities?: string[];
  managed_by?: string;
  telephony_mode?: LabsTelephonyMode | string;
  [extra: string]: unknown;
}

export interface LabsPhoneNumberSearchResponse {
  numbers: LabsPhoneNumberOption[];
  search_context?: Record<string, unknown>;
}

export interface LabsPhoneNumberRecord {
  number_id?: string;
  phone_number?: string;
  status?: string;
  friendly_name?: string;
  number_type?: string;
  monthly_cost?: number;
  provisioned_at?: string;
  capabilities?: string[];
  managed_by?: string;
  telephony_mode?: LabsTelephonyMode | string;
  [extra: string]: unknown;
}

export interface LabsPhoneNumberListOptions {
  agencyId?: string;
  activeOnly?: boolean;
}

export interface LabsPhoneNumberListResponse {
  numbers: LabsPhoneNumberRecord[];
  telephony?: Record<string, unknown>;
}

export interface LabsPhoneNumberProvisionRequest {
  agencyId?: string;
  agency_id?: string;
  phoneNumber?: string;
  phone_number?: string;
  friendlyName?: string;
  friendly_name?: string;
  departmentId?: string;
  department_id?: string;
  agentKey?: string;
  agent_key?: string;
  agentId?: string;
  agent_id?: string;
  agentName?: string;
  agent_name?: string;
  presetKey?: string;
  preset_key?: string;
  numberStrategy?: LabsNumberStrategy;
  number_strategy?: LabsNumberStrategy;
  numberPool?: string;
  number_pool?: string;
  premium?: boolean;
  style?: LabsAgentStyle;
  agentStyle?: LabsAgentStyle;
  agent_style?: LabsAgentStyle;
  direction?: LabsAgentStyle;
  telephony?: LabsTelephonyConfig;
  metadata?: Record<string, unknown>;
}

export interface LabsPhoneNumberAssignRequest extends Omit<LabsPhoneNumberProvisionRequest, "phoneNumber" | "phone_number" | "departmentId" | "department_id"> {}

export interface LabsPhoneNumberReleaseRequest {
  agencyId?: string;
  agency_id?: string;
  reason?: string;
  returnToPool?: boolean;
  return_to_pool?: boolean;
  metadata?: Record<string, unknown>;
}

export interface LabsPhoneNumberProvisionResponse {
  success: boolean;
  number: LabsPhoneNumberRecord;
  assignment?: Record<string, unknown>;
  telephony?: Record<string, unknown>;
  [extra: string]: unknown;
}

export interface LabsPhoneNumberAssignResponse {
  success: boolean;
  number: LabsPhoneNumberRecord;
  assignment?: Record<string, unknown>;
}

export interface LabsPhoneNumberReleaseResponse {
  success: boolean;
  number?: LabsPhoneNumberRecord;
  released?: boolean;
  returned_to_pool?: boolean;
  [extra: string]: unknown;
}

export interface LabsPhoneNumberBuyAndAssignRequest extends LabsPhoneNumberProvisionRequest {
  search?: LabsPhoneNumberSearchOptions;
}

export interface LabsTelephonyResponse {
  telephony: Record<string, unknown>;
  default?: Record<string, unknown>;
  byok?: Record<string, unknown>;
}

export interface LabsTelephonyConfigureResponse {
  success: boolean;
  telephony: Record<string, unknown>;
}

export interface CreateLabsAgentWithNumberRequest extends CreateLabsAgentRequest {
  number?: LabsPhoneNumberBuyAndAssignRequest;
}

export interface CreateLabsAgentWithNumberResponse extends CreateLabsAgentResponse {
  number?: LabsPhoneNumberProvisionResponse;
}

export interface LabsAgentResponse {
  id?: string;
  agency_id?: string;
  agent_type?: LabsAgentType | string;
  agent_key?: string;
  source_id?: string;
  display_name?: string;
  runtime_mode?: string;
  preset_key?: string;
  profile?: Record<string, unknown>;
  runtime?: Record<string, unknown>;
  [extra: string]: unknown;
}

export interface CreateLabsAgentResponse {
  success: boolean;
  agent: LabsAgentResponse;
  runtime: Record<string, unknown>;
  widget?: {
    widget_key?: string;
    snippet?: string;
    [extra: string]: unknown;
  };
  [extra: string]: unknown;
}

export interface ListLabsAgentsResponse {
  agents: LabsAgentResponse[];
  total: number;
}

export interface GetLabsAgentResponse {
  agent: LabsAgentResponse;
}

export interface STTResult {
  transcript: string;
  languages: string[];
  duration: number;
  raw?: unknown;
}

/** A whisper/nudge event you log for the console feed + metrics (zero-billed). */
export interface NudgeEvent {
  text: string;
  session_id?: string;
  provider?: string;
  confidence?: number;
  injected?: boolean;
  kind?: string;
  language?: string;
  emotion?: string;
  intent?: string;
  urgency?: number;
  latency_ms?: number;
  model?: string;
  turns?: number;
}

/** A post-call report — the fuel the optimizer improves against. */
export interface CallReportInput {
  session_id?: string;
  agent?: string;
  score?: number;
  outcome?: string;
  summary?: string;
  nudges?: number;
  turns?: number;
  language?: string;
  /** Full "role: text" transcript — enables automatic post-call analysis. */
  transcript?: string;
  /** Structured turns (alternative to transcript) for post-call analysis. */
  messages?: ClassifyMessage[];
  /** Deterministic runtime signals blended into the objective value. */
  ground_truth?: GroundTruthInput;
  [extra: string]: unknown;
}

/** One turn of a finished call handed to the classifier. */
export interface ClassifyMessage {
  role: "caller" | "agent" | "whisper" | string;
  text: string;
}

/** Deterministic runtime ground truth (the same signals postcall scoring reads). */
export interface GroundTruthInput {
  booking_requested?: boolean;
  booking_verified?: boolean;
  delivery_requested?: boolean;
  delivery_verified?: boolean;
  end_call_claims_verified?: boolean;
  unverified_claims?: string[];
}

export interface ClassifyCallInput {
  sessionId?: string;
  agent?: string;
  transcript?: string;
  messages?: ClassifyMessage[];
  groundTruth?: GroundTruthInput;
  nudges?: number;
}

/** The labels post-call analysis generates for one finished call. */
export interface CallClassification {
  /** Did the call achieve the agent's objective? */
  achieved: boolean;
  objective_achieved: boolean;
  /** LLM objective score in [0,1] (before ground-truth blending). */
  objective_score: number;
  /** Blended objective value: (1-w)*LLM + w*ground-truth when supplied. */
  objective_value: number;
  ground_truth_score: number | null;
  /** Per-criterion verdicts keyed by the objective's criterion names. */
  criteria: Record<string, boolean | string>;
  failure_reasons: string[];
  summary: string;
  /** Standing-directive version in force during the call (for A/B trends). */
  directive_version: number;
  agent: string;
  [extra: string]: unknown;
}

export interface CallReportResult {
  recorded: boolean;
  /** Present when automatic post-call analysis ran — the generated labels. */
  analysis?: CallClassification;
  [extra: string]: unknown;
}

export interface BuilderTurn {
  role: "caller" | "agent" | "whisper";
  text: string;
}

export interface BuilderChatResult {
  whisper: string;
  agent_reply: string;
  emotion?: string;
  language?: string;
  intent?: string;
  oracle_ms?: number;
  standing_version?: number;
}

/** One auto-generated adversarial scenario (from the agent's own prompt). */
export interface QAScenario {
  title: string;
  persona: string;
  opener: string;
  assertion: string;
}

/** The 5-level SSR nominal scale. */
export type SSRLabel = "poorly" | "ok" | "good" | "great" | "perfectly";

/** An SSR grade: nominal label -> deterministic score + bucket distribution. */
export interface SSRGrade {
  label: SSRLabel;
  score: number;
  /** Probability mass over 10 score buckets [0-0.1, ..., 0.9-1.0]. */
  distribution: number[];
  rationale: string;
}

/** Result of qa.suite(): generated scenarios played vs the real agent config. */
export interface QASuiteResult {
  agent: string;
  objective: string;
  supervised: boolean;
  turns: number;
  results: Array<{
    scenario: string;
    title: string;
    persona: string;
    assertion: string;
    passed: boolean;
    evidence: string;
    ssr: SSRGrade;
    transcript: BuilderTurn[];
  }>;
  summary: {
    tests: number;
    passed: number;
    avg_ssr_score: number;
    ssr_histogram: Record<SSRLabel, number>;
    oracle_calls_billed: number;
  };
}

export interface QAResult {
  agent: string;
  turns: number;
  results: Array<{
    scenario: string;
    title: string;
    assertion: string;
    unsupervised: { passed: boolean; score: number; evidence: string; whispers: number };
    supervised: { passed: boolean; score: number; evidence: string; whispers: number };
    lift: number;
  }>;
  summary: {
    scenarios: number;
    passed_supervised: number;
    passed_unsupervised: number;
    avg_lift: number;
    oracle_calls_billed: number;
  };
}

export class SupafoneLabsError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    readonly body?: unknown,
  ) {
    super(message);
    this.name = "SupafoneLabsError";
  }
}

const DEFAULT_BASE = "https://api.labs.supafone.ai";
const DEFAULT_SUPAFONE_API_BASE = "https://api.supafone.ai";

const COACH_SYSTEM =
  "You are the coaching core of a second mind for a live voice agent. Read the " +
  "conversation and return ONE short, silent directive the agent reads but never " +
  "speaks aloud — a correction or nudge, phrased imperatively. If nothing needs " +
  "correcting, return an empty string.";

export class SupafoneLabs {
  readonly baseUrl: string;
  readonly supafoneApiBaseUrl: string;
  readonly appUrl: string;
  private readonly apiKey: string;
  private readonly supafoneApiKey: string;
  private readonly timeoutMs: number;
  private readonly postCallAnalysis: boolean;
  /** Client default for the Voice Watcher framework (supervision + QA + scoring). */
  readonly voiceWatcher: boolean;
  private sessionToken?: string;
  private accountToken?: string;
  private accountSessionToken?: string;
  private readonly accountEmail?: string;
  private readonly accountPassword?: string;

  readonly labs: LabsNamespace;
  readonly builder: BuilderNamespace;
  readonly qa: QANamespace;
  readonly optimizer: OptimizerNamespace;
  readonly campaigns: CampaignsNamespace;

  constructor(opts: SupafoneLabsOptions) {
    const hasAccountAuth = !!(opts?.accountToken || (opts?.accountEmail && opts?.accountPassword));
    if (!opts?.apiKey && !hasAccountAuth) {
      throw new SupafoneLabsError(
        "apiKey is required — or, for campaigns/calls, pass accountToken or accountEmail + accountPassword",
      );
    }
    this.apiKey = opts.apiKey ?? "";
    this.baseUrl = (opts.baseUrl ?? DEFAULT_BASE).replace(/\/$/, "");
    this.supafoneApiKey = opts.supafoneApiKey ?? this.apiKey;
    this.supafoneApiBaseUrl = (opts.supafoneApiBaseUrl ?? DEFAULT_SUPAFONE_API_BASE).replace(/\/$/, "");
    this.appUrl = (opts.appUrl ?? "https://app.supafone.ai").replace(/\/$/, "");
    this.timeoutMs = opts.timeoutMs ?? 30_000;
    this.postCallAnalysis = opts.postCallAnalysis ?? false;
    // Precedence: explicit voiceWatcher > voice_watcher (snake) > labs (deprecated) > true.
    this.voiceWatcher = opts.voiceWatcher ?? opts.voice_watcher ?? opts.labs ?? true;
    this.sessionToken = opts.sessionToken;
    this.accountToken = opts.accountToken;
    this.accountEmail = opts.accountEmail;
    this.accountPassword = opts.accountPassword;
    // One-key auth: the product API accepts `sl_` Labs keys as bearer
    // credentials, so a lone sl_ credential fills whichever lane wasn't given.
    if (!this.accountToken && this.apiKey.startsWith("sl_")) {
      this.accountToken = this.apiKey;
    }
    if (!this.apiKey && this.accountToken?.startsWith("sl_")) {
      this.apiKey = this.accountToken;
    }
    this.labs = new LabsNamespace(this);
    this.builder = new BuilderNamespace(this);
    this.qa = new QANamespace(this);
    this.optimizer = new OptimizerNamespace(this);
    this.campaigns = new CampaignsNamespace(this);
  }

  /** True once login() (or a passed sessionToken) is in effect. */
  get isLoggedIn(): boolean {
    return !!this.sessionToken;
  }

  /**
   * Exchange email/password for a console session. Required by the builder.*
   * methods and qa.run (which are account/session-scoped, not key-scoped).
   */
  async login(email: string, password: string): Promise<void> {
    const d = await this.request<{ token?: string }>("POST", "/v1/auth/login", { email, password });
    if (!d.token) throw new SupafoneLabsError("Login succeeded but returned no token");
    this.sessionToken = d.token;
  }

  /** @internal Authenticated JSON request. `useSession` prefers the login token. */
  async request<T>(method: string, path: string, body?: unknown, useSession = false): Promise<T> {
    const token = useSession && this.sessionToken ? this.sessionToken : this.apiKey;
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
    try {
      const res = await fetch(this.baseUrl + path, {
        method,
        signal: ctrl.signal,
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const text = await res.text();
      const parsed = text ? safeJson(text) : {};
      if (!res.ok) {
        const detail = (parsed as { detail?: string })?.detail ?? text ?? `HTTP ${res.status}`;
        throw new SupafoneLabsError(`${method} ${path}: ${detail}`, res.status, parsed);
      }
      return parsed as T;
    } finally {
      clearTimeout(timer);
    }
  }

  /** @internal Authenticated JSON request to the Supafone app API (`/api/v1/labs/*`). */
  async requestSupafoneApi<T>(method: string, path: string, body?: unknown): Promise<T> {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
    try {
      const res = await fetch(this.supafoneApiBaseUrl + path, {
        method,
        signal: ctrl.signal,
        headers: { Authorization: `Bearer ${this.supafoneApiKey}`, "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const text = await res.text();
      const parsed = text ? safeJson(text) : {};
      if (!res.ok) {
        const detail = (parsed as { detail?: string })?.detail ?? text ?? `HTTP ${res.status}`;
        throw new SupafoneLabsError(`${method} ${path}: ${detail}`, res.status, parsed);
      }
      return parsed as T;
    } finally {
      clearTimeout(timer);
    }
  }

  /**
   * Exchange the account email/password for a product-API JWT (the same login
   * as app.supafone.ai). Called lazily by campaigns/calls — call directly only
   * to fail fast.
   */
  async accountLogin(email?: string, password?: string): Promise<string> {
    const useEmail = email ?? this.accountEmail;
    const usePassword = password ?? this.accountPassword;
    if (!useEmail || !usePassword) {
      throw new SupafoneLabsError(
        "Not authenticated: pass accountToken, or accountEmail + accountPassword",
      );
    }
    const body = await this.accountHttp<{ token?: string; access_token?: string }>(
      "POST",
      "/api/v1/auth/login",
      { email: useEmail, password: usePassword },
      "",
    );
    const token = body.access_token || body.token;
    if (!token) throw new SupafoneLabsError("Login succeeded but returned no token");
    this.accountSessionToken = token;
    return token;
  }

  /**
   * @internal JSON request to the Supafone product API with the ACCOUNT JWT
   * (campaigns + real calls). A minted token that expires gets one transparent
   * re-login; an explicit accountToken is the caller's to refresh.
   */
  async requestAccountApi<T>(method: string, path: string, body?: unknown): Promise<T> {
    const token = this.accountToken || this.accountSessionToken || (await this.accountLogin());
    try {
      return await this.accountHttp<T>(method, path, body, token);
    } catch (err) {
      const expired = err instanceof SupafoneLabsError && err.status === 401;
      if (expired && !this.accountToken && this.accountEmail && this.accountPassword) {
        this.accountSessionToken = undefined;
        return this.accountHttp<T>(method, path, body, await this.accountLogin());
      }
      throw err;
    }
  }

  /** @internal Multipart file POST with the same auth/re-login as requestAccountApi. */
  async requestAccountUpload<T>(path: string, file: Uint8Array | ArrayBuffer | Blob, filename: string): Promise<T> {
    const token = this.accountToken || this.accountSessionToken || (await this.accountLogin());
    const send = async (bearer: string): Promise<T> => {
      const blob = file instanceof Blob ? file : new Blob([file as BlobPart], { type: "application/pdf" });
      const form = new FormData();
      form.append("file", blob, filename);
      const res = await fetch(this.supafoneApiBaseUrl + path, {
        method: "POST",
        headers: { Authorization: `Bearer ${bearer}` },
        body: form,
      });
      const text = await res.text();
      const parsed = text ? safeJson(text) : {};
      if (!res.ok) {
        const detail = (parsed as { detail?: string })?.detail ?? text ?? `HTTP ${res.status}`;
        throw new SupafoneLabsError(`POST ${path}: ${detail}`, res.status, parsed);
      }
      return parsed as T;
    };
    try {
      return await send(token);
    } catch (err) {
      const expired = err instanceof SupafoneLabsError && err.status === 401;
      if (expired && !this.accountToken && this.accountEmail && this.accountPassword) {
        this.accountSessionToken = undefined;
        return send(await this.accountLogin());
      }
      throw err;
    }
  }

  /** @internal Raw product-API request with an explicit bearer ("" = none). */
  private async accountHttp<T>(method: string, path: string, body: unknown, token: string): Promise<T> {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers.Authorization = `Bearer ${token}`;
      const res = await fetch(this.supafoneApiBaseUrl + path, {
        method,
        signal: ctrl.signal,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const text = await res.text();
      const parsed = text ? safeJson(text) : {};
      if (!res.ok) {
        const detail = (parsed as { detail?: string })?.detail ?? text ?? `HTTP ${res.status}`;
        throw new SupafoneLabsError(`${method} ${path}: ${detail}`, res.status, parsed);
      }
      return parsed as T;
    } finally {
      clearTimeout(timer);
    }
  }

  /**
   * PLACE A REAL OUTBOUND PHONE CALL: dials toNumber from the account's
   * calling provider and bridges the voice agent onto the line.
   */
  async placeCall(opts: { agentId: string; toNumber: string }): Promise<PlaceCallResult> {
    if (!opts?.agentId) throw new SupafoneLabsError("agentId is required (see listVoiceAgents())");
    if (!opts?.toNumber) throw new SupafoneLabsError("toNumber is required (E.164, e.g. +15551234567)");
    return this.requestAccountApi<PlaceCallResult>("POST", "/api/v1/phone/test-call", {
      agent_id: opts.agentId,
      to_number: opts.toNumber,
    });
  }

  /** The account's voice agents — pick an agent id for campaigns/calls. */
  async listVoiceAgents(): Promise<{ agents: Record<string, unknown>[] }> {
    return this.requestAccountApi("GET", "/api/v1/agents");
  }

  /**
   * Scan a website for its branding: business name, brand colors, logo,
   * favicon, Open Graph metadata, page images, and key same-domain pages.
   */
  async scanBrand(url: string): Promise<BrandScanResult> {
    if (!url?.trim()) throw new SupafoneLabsError("url is required (the website to scan)");
    return this.requestAccountApi("POST", "/api/v1/agents/brand-scan", { url: url.trim() });
  }

  /**
   * Generate a guided intake form (IntakeConfig) from a plain-language
   * description. Pass agentId to ground it in that agent's business, and
   * apply:true to write it onto the agent.
   */
  async generateIntakeForm(opts: {
    description: string;
    agentId?: string;
    industry?: string;
    apply?: boolean;
  }): Promise<GenerateIntakeResult> {
    if (!opts?.description?.trim()) {
      throw new SupafoneLabsError("description is required — what should the form collect?");
    }
    if (opts.apply && !opts.agentId) {
      throw new SupafoneLabsError("apply:true needs an agentId (see listVoiceAgents())");
    }
    const payload: Record<string, unknown> = { description: opts.description.trim() };
    if (opts.industry) payload.industry = opts.industry;
    if (opts.agentId) {
      payload.apply = Boolean(opts.apply);
      return this.requestAccountApi(
        "POST",
        `/api/v1/agents/${encodeURIComponent(opts.agentId)}/generate-intake`,
        payload,
      );
    }
    return this.requestAccountApi("POST", "/api/v1/agents/generate-intake", payload);
  }

  /** Raw oracle completion — full control over messages and model. */
  async oracle(req: OracleRequest): Promise<OracleResult> {
    return this.request<OracleResult>("POST", "/v1/oracle/complete", {
      messages: req.messages,
      model: req.model ?? "supafone-labs-oracle",
      max_tokens: req.maxTokens ?? 256,
      ...(req.temperature !== undefined ? { temperature: req.temperature } : {}),
    });
  }

  /**
   * The one-liner: hand it the running transcript, get back a silent directive
   * (empty string when the agent is doing fine).
   */
  async whisper(transcript: string, opts: WhisperOptions = {}): Promise<string> {
    const system = opts.guardrails ? `${COACH_SYSTEM}\n\nOperator rules:\n${opts.guardrails}` : COACH_SYSTEM;
    const out = await this.oracle({
      model: opts.model,
      maxTokens: opts.maxTokens ?? 120,
      ...(opts.temperature !== undefined ? { temperature: opts.temperature } : {}),
      messages: [
        { role: "system", content: system },
        { role: "user", content: transcript },
      ],
    });
    return out.text.trim();
  }

  /** Hosted TTS — returns raw audio bytes (WAV/PCM per voice). */
  async tts(text: string, voice = "supafone-labs-calm-en"): Promise<Uint8Array> {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
    try {
      const res = await fetch(this.baseUrl + "/v1/tts", {
        method: "POST",
        signal: ctrl.signal,
        headers: { Authorization: `Bearer ${this.apiKey}`, "Content-Type": "application/json" },
        body: JSON.stringify({ voice, text }),
      });
      if (!res.ok) throw new SupafoneLabsError(`tts: ${await res.text()}`, res.status);
      return new Uint8Array(await res.arrayBuffer());
    } finally {
      clearTimeout(timer);
    }
  }

  /** Convenience alias for voice preview UI/buttons. */
  previewVoice(
    voice = "supafone-labs-calm-en",
    text = "Hi, this is your Supafone agent voice preview.",
  ): Promise<Uint8Array> {
    return this.tts(text, voice);
  }

  /** Hosted STT for a finished audio clip — returns transcript + language tags. */
  async stt(
    audio: Uint8Array | ArrayBuffer,
    opts: { language?: string; mimetype?: string } = {},
  ): Promise<STTResult> {
    const bytes = audio instanceof ArrayBuffer ? new Uint8Array(audio) : audio;
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
    try {
      const res = await fetch(
        this.baseUrl + `/v1/stt?language=${encodeURIComponent(opts.language ?? "multi")}`,
        {
          method: "POST",
          signal: ctrl.signal,
          headers: {
            Authorization: `Bearer ${this.apiKey}`,
            "Content-Type": opts.mimetype ?? "application/octet-stream",
          },
          body: bytes as unknown as BodyInit,
        },
      );
      if (!res.ok) throw new SupafoneLabsError(`stt: ${await res.text()}`, res.status);
      const d = (await res.json()) as {
        transcript?: string;
        languages?: string[];
        duration?: number;
        results?: { channels?: Array<{ alternatives?: Array<{ transcript?: string }> }> };
      };
      // Flattened shape first; fall back to raw Deepgram nesting for older gateways.
      const transcript =
        d.transcript ?? d.results?.channels?.[0]?.alternatives?.[0]?.transcript ?? "";
      return { transcript, languages: d.languages ?? [], duration: d.duration ?? 0, raw: d };
    } finally {
      clearTimeout(timer);
    }
  }

  /**
   * Open a live multilingual transcription socket. Feed PCM frames with
   * `feed()`; language-tagged results arrive via `onResult`. Uses the global
   * WebSocket (browser, Node 22+); pass one in `opts.WebSocketImpl` on older Node.
   */
  liveTranscribe(opts: LiveTranscribeOptions = {}): LiveTranscription {
    return new LiveTranscription(this, opts);
  }

  /** Remaining prepaid balance. */
  balance(): Promise<Balance> {
    return this.request<Balance>("GET", "/v1/billing/balance");
  }

  /** Today's usage against your plan caps (oracle/tts/stt/…). */
  usage(): Promise<UsageToday> {
    return this.request<UsageToday>("GET", "/v1/usage");
  }

  /** The auditable whisper/billing log. */
  logs(limit = 100): Promise<{ logs: LabsLogEntry[] }> {
    return this.request("GET", `/v1/logs?limit=${limit}`);
  }

  /** Live audit-log stream. Works in Node 18+ and browsers via fetch streaming. */
  async *streamLogs(opts: StreamLogsOptions = {}): AsyncGenerator<LabsLogEntry> {
    const q = new URLSearchParams({
      limit: String(opts.limit ?? 100),
      poll_ms: String(opts.pollMs ?? 1000),
      snapshot: String(opts.snapshot ?? true),
    });
    if (opts.afterId !== undefined) q.set("after_id", String(opts.afterId));
    const res = await fetch(`${this.baseUrl}/v1/logs/stream?${q}`, {
      method: "GET",
      signal: opts.signal,
      headers: { Authorization: `Bearer ${this.apiKey}` },
    });
    if (!res.ok) throw new SupafoneLabsError(`streamLogs: ${await res.text()}`, res.status);
    if (!res.body) throw new SupafoneLabsError("streamLogs: response body is not readable");
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let split = buffer.indexOf("\n\n");
        while (split >= 0) {
          const raw = buffer.slice(0, split);
          buffer = buffer.slice(split + 2);
          const parsed = parseSseLog(raw);
          if (parsed) yield parsed;
          split = buffer.indexOf("\n\n");
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  /** The structured whisper feed (what the console shows). */
  nudges(limit = 50): Promise<{ nudges: unknown[] }> {
    return this.request("GET", `/v1/nudges?limit=${limit}`);
  }

  /** Aggregated metrics — injection rate, latency, by-dimension breakdowns. */
  metrics(days = 7): Promise<Record<string, unknown>> {
    return this.request("GET", `/v1/metrics?days=${days}`);
  }

  /** Log one whisper event (zero-billed) for the console feed + metrics. */
  reportNudge(event: NudgeEvent): Promise<{ ok?: boolean }> {
    return this.request("POST", "/v1/events/nudge", event);
  }

  /**
   * File a post-call report — the fuel optimizer.improve() learns from.
   *
   * With `postCallAnalysis: true` on the client and a transcript (or
   * messages) present, the call is automatically classified first: the
   * oracle labels it against the agent's objective (achieved/missed,
   * per-criterion verdicts, failure reasons) and files the enriched report
   * server-side. The generated labels come back on `analysis`. Analysis is
   * best-effort — on any failure the plain zero-billed report still lands.
   */
  async reportCall(report: CallReportInput): Promise<CallReportResult> {
    const { transcript, messages, ground_truth, ...plain } = report;
    const analyzable = !!transcript || !!(messages && messages.length);
    if (this.postCallAnalysis && analyzable) {
      try {
        const analysis = await this.classifyCall({
          sessionId: report.session_id,
          agent: report.agent,
          transcript,
          messages,
          groundTruth: ground_truth,
          nudges: report.nudges,
        });
        // classifyCall files the enriched report server-side — don't double-file.
        return { recorded: true, analysis };
      } catch {
        /* analysis is best-effort — fall through to the plain report */
      }
    }
    const out = await this.request<Record<string, unknown>>("POST", "/v1/events/call_report", plain);
    return { recorded: true, ...out };
  }

  /**
   * Post-call analysis for one finished call: classify it against the agent's
   * objective and get labels back — achieved/missed, per-criterion verdicts,
   * failure reasons, and the blended objective value. Files an enriched call
   * report server-side (feeding optimizer.improve() and objective stats).
   * Billed one oracle call.
   */
  classifyCall(input: ClassifyCallInput): Promise<CallClassification> {
    return this.request<CallClassification>(
      "POST",
      "/v1/calls/classify",
      compact({
        session_id: input.sessionId,
        agent: input.agent ?? "builder",
        transcript: input.transcript,
        messages: input.messages,
        ground_truth: input.groundTruth,
        nudges: input.nudges,
      }),
    );
  }

  /** Available oracle model ids (live vendor catalog). */
  async models(): Promise<string[]> {
    const d = await this.request<{ models: Array<string | { id: string }> }>("GET", "/v1/models");
    return d.models.map((m) => (typeof m === "string" ? m : m.id));
  }

  /** Available TTS voice ids. */
  async voices(): Promise<string[]> {
    const d = await this.request<{ voices: Array<string | { voice?: string; id?: string }> }>(
      "GET",
      "/v1/voices",
    );
    return d.voices.map((v) => (typeof v === "string" ? v : (v.voice ?? v.id ?? ""))).filter(Boolean);
  }

  /** Full hosted voice catalog with provider live/configured flags. */
  voiceCatalog(): Promise<{ voices: Array<Record<string, unknown>> }> {
    return this.request("GET", "/v1/voices");
  }
}

export interface LiveTranscribeOptions {
  language?: string; // "multi" for code-switching
  encoding?: string; // "linear16"
  sampleRate?: number; // 16000
  onResult?: (r: LiveResult) => void;
  onError?: (e: unknown) => void;
  onClose?: () => void;
  /** Inject a WebSocket implementation for Node < 22 (e.g. `ws`). */
  WebSocketImpl?: typeof WebSocket;
}

export interface LiveResult {
  transcript: string;
  languages: string[];
  isFinal: boolean;
}

class LiveTranscription {
  private ws: WebSocket;

  constructor(sm: SupafoneLabs, opts: LiveTranscribeOptions) {
    const WS = opts.WebSocketImpl ?? (globalThis as { WebSocket?: typeof WebSocket }).WebSocket;
    if (!WS) throw new SupafoneLabsError("No WebSocket available — pass opts.WebSocketImpl (e.g. the `ws` package)");
    const base = sm.baseUrl.replace(/^http/, "ws");
    const q = new URLSearchParams({
      // The key rides in the query string because browsers can't set WS headers.
      api_key: (sm as unknown as { apiKey: string }).apiKey,
      language: opts.language ?? "multi",
      encoding: opts.encoding ?? "linear16",
      sample_rate: String(opts.sampleRate ?? 16000),
    });
    this.ws = new WS(`${base}/v1/stt/live?${q}`);
    this.ws.addEventListener?.("message", (ev: MessageEvent) => {
      const d = safeJson(typeof ev.data === "string" ? ev.data : String(ev.data)) as {
        channel?: { alternatives?: Array<{ transcript?: string; languages?: string[] }> };
        is_final?: boolean;
      };
      const alt = d.channel?.alternatives?.[0];
      if (alt?.transcript && opts.onResult) {
        opts.onResult({ transcript: alt.transcript, languages: alt.languages ?? [], isFinal: !!d.is_final });
      }
    });
    if (opts.onError) this.ws.addEventListener?.("error", opts.onError as EventListener);
    if (opts.onClose) this.ws.addEventListener?.("close", opts.onClose);
  }

  /** Send one PCM audio frame. */
  feed(frame: Uint8Array | ArrayBuffer): void {
    this.ws.send(frame as ArrayBuffer);
  }

  /** Signal end-of-stream and close. */
  close(): void {
    try {
      this.ws.send(JSON.stringify({ type: "CloseStream" }));
    } catch {
      /* already closing */
    }
    this.ws.close();
  }

  get socket(): WebSocket {
    return this.ws;
  }
}

/** Programmatic hosted Supafone agents, inside the Supafone API. */
// ---------------------------------------------------------------------------
// Campaigns — the outbound AI campaign engine the app.supafone.ai builder
// drives, packaged. Account-JWT authenticated (accountToken / accountEmail +
// accountPassword on the client options).
// ---------------------------------------------------------------------------

export interface PlaceCallResult {
  success: boolean;
  simulated?: boolean;
  call_sid?: string | null;
  provider?: string;
}

export interface CampaignRecipientInput {
  name?: string;
  phone?: string;
  email?: string;
  /** Warm-outreach consent — required before any voice/email touch. */
  outreach_consent?: string;
  [field: string]: unknown;
}

export interface CampaignSummary {
  id: string;
  name: string;
  goal: string;
  status: string;
  agent_id?: string | null;
  stats?: Record<string, unknown>;
  settings?: Record<string, unknown>;
  [field: string]: unknown;
}

export interface CampaignLiveCall {
  id: string;
  status: string;
  /** Portal deep link to watch this call (live transcript while in flight). */
  listen_url: string;
  [field: string]: unknown;
}

export interface CampaignLiveView {
  campaign_id: string;
  in_flight: CampaignLiveCall[];
  /** Developer-portal link showing this campaign's agents/calls live. */
  portal_url: string;
  stats?: Record<string, unknown> | null;
}

export interface CampaignUpdateInput {
  name?: string;
  goal?: string;
  agentId?: string;
  emailSubject?: string;
  emailBody?: string;
  cadence?: { channel: "voice" | "email"; delay_hours: number }[];
  settings?: Record<string, unknown>;
}

export interface BrandScanResult {
  url: string;
  business_name: string;
  colors: string[];
  primary_color: string;
  theme_color: string;
  css_brand_colors: string[];
  logo_url: string;
  favicon_url: string;
  og: { title: string; description: string; image: string };
  images: string[];
  key_urls: string[];
  scrape_source: string;
  fallback_used: boolean;
  error?: string | null;
}

export interface GenerateIntakeResult {
  intake: Record<string, unknown>;
  /** false means the deterministic industry-workflow fallback was used. */
  generated: boolean;
  applied: boolean;
  agent?: Record<string, unknown>;
}

export interface CampaignConfigReport {
  valid: boolean;
  errors: string[];
  warnings: string[];
  summary: Record<string, unknown>;
}

export interface CampaignConfigApplyResult {
  campaign: CampaignSummary;
  created: boolean;
  added: number;
  launched: boolean;
  /** Branding scan / intake generation results for the doc's agent-facing blocks. */
  extras?: Record<string, unknown> | null;
  report: CampaignConfigReport;
}

/**
 * Typical flow:
 * ```ts
 * const sf = new Supafone({ accountEmail, accountPassword });
 * const { agents } = await sf.listVoiceAgents();
 * const { campaign } = await sf.campaigns.create({ name: "Q3 win-back", goal: "reengage", agentId: agents[0].id });
 * await sf.campaigns.applyPreset(campaign.id, "win_back");
 * await sf.campaigns.addRecipients(campaign.id, [{ name: "Jane", phone: "+15551234567", outreach_consent: "yes" }]);
 * await sf.campaigns.launch(campaign.id);
 * const live = await sf.campaigns.live(campaign.id); // in-flight calls + portal links
 * ```
 */
class CampaignsNamespace {
  constructor(private sm: SupafoneLabs) {}

  list(opts: { accountId?: string } = {}): Promise<{ campaigns: CampaignSummary[] }> {
    const query = opts.accountId ? `?${new URLSearchParams({ account_id: opts.accountId })}` : "";
    return this.sm.requestAccountApi("GET", `/api/v1/campaigns${query}`);
  }

  create(opts: { name?: string; goal?: string; agentId?: string; accountId?: string } = {}): Promise<{ campaign: CampaignSummary }> {
    return this.sm.requestAccountApi("POST", "/api/v1/campaigns", compact({
      name: opts.name ?? "New campaign",
      goal: opts.goal ?? "book",
      agent_id: opts.agentId,
      account_id: opts.accountId,
    }));
  }

  get(campaignId: string): Promise<{ campaign: CampaignSummary }> {
    return this.sm.requestAccountApi("GET", `/api/v1/campaigns/${encodeURIComponent(campaignId)}`);
  }

  update(campaignId: string, input: CampaignUpdateInput): Promise<{ campaign: CampaignSummary }> {
    const payload = compact({
      name: input.name,
      goal: input.goal,
      agent_id: input.agentId,
      email_subject: input.emailSubject,
      email_body: input.emailBody,
      cadence: input.cadence,
      settings: input.settings,
    });
    if (!Object.keys(payload as Record<string, unknown>).length) {
      throw new SupafoneLabsError("Nothing to update — pass name, goal, agentId, emailSubject, emailBody, cadence, or settings");
    }
    return this.sm.requestAccountApi("PUT", `/api/v1/campaigns/${encodeURIComponent(campaignId)}`, payload);
  }

  /** Add consented leads: [{name, phone, email, outreach_consent: "yes"}]. */
  addRecipients(campaignId: string, recipients: CampaignRecipientInput[]): Promise<{ added: number; stats: Record<string, unknown> }> {
    if (!Array.isArray(recipients) || !recipients.length) {
      throw new SupafoneLabsError("recipients must be a non-empty array of lead rows");
    }
    return this.sm.requestAccountApi("POST", `/api/v1/campaigns/${encodeURIComponent(campaignId)}/recipients`, { recipients });
  }

  recipients(campaignId: string): Promise<{ recipients: Record<string, unknown>[] }> {
    return this.sm.requestAccountApi("GET", `/api/v1/campaigns/${encodeURIComponent(campaignId)}/recipients`);
  }

  /** Starts REAL calls/emails on the cadence immediately. */
  launch(campaignId: string): Promise<{ campaign: CampaignSummary }> {
    return this.sm.requestAccountApi("POST", `/api/v1/campaigns/${encodeURIComponent(campaignId)}/launch`, {});
  }

  pause(campaignId: string): Promise<{ campaign: CampaignSummary }> {
    return this.sm.requestAccountApi("POST", `/api/v1/campaigns/${encodeURIComponent(campaignId)}/pause`, {});
  }

  /** Built-in playbooks + the account's saved custom presets. */
  async presets(): Promise<{ built_in: Record<string, unknown>[]; custom: Record<string, unknown>[] }> {
    const builtIn = await this.sm.requestAccountApi<{ presets: Record<string, unknown>[] }>(
      "GET",
      "/api/v1/campaigns/outbound-presets",
    );
    let custom: Record<string, unknown>[] = [];
    try {
      const mine = await this.sm.requestAccountApi<{ presets: Record<string, unknown>[] }>(
        "GET",
        "/api/v1/campaigns/custom-presets",
      );
      custom = mine.presets ?? [];
    } catch {
      /* custom presets need account scope — built-ins still return */
    }
    return { built_in: builtIn.presets ?? [], custom };
  }

  /** Materialize a preset (goal, questions, scripts, signing doc) in one write. */
  applyPreset(campaignId: string, presetId: string): Promise<{ campaign: CampaignSummary }> {
    return this.sm.requestAccountApi("POST", `/api/v1/campaigns/${encodeURIComponent(campaignId)}/apply-preset`, {
      preset_id: presetId,
    });
  }

  stats(campaignId: string): Promise<{ stats: Record<string, unknown> }> {
    return this.sm.requestAccountApi("GET", `/api/v1/campaigns/${encodeURIComponent(campaignId)}/stats`);
  }

  /** The live funnel + the campaign's most recent calls (newest first). */
  activity(campaignId: string): Promise<{ stats?: Record<string, unknown>; calls?: Record<string, unknown>[] }> {
    return this.sm.requestAccountApi("GET", `/api/v1/campaigns/${encodeURIComponent(campaignId)}/activity`);
  }

  /**
   * In-flight calls right now, each with a portal link to watch/listen. Poll
   * getCall(callId) (or open the link) for the transcript as it grows.
   */
  async live(campaignId: string): Promise<CampaignLiveView> {
    const activity = await this.activity(campaignId);
    const inFlight: CampaignLiveCall[] = [];
    for (const call of activity.calls ?? []) {
      const status = String((call as { status?: unknown }).status ?? "");
      if (status === "initiated" || status === "dialing" || status === "in_progress") {
        const id = String((call as { id?: unknown }).id ?? "");
        inFlight.push({
          ...(call as Record<string, unknown>),
          id,
          status,
          listen_url: `${this.sm.appUrl}/app/calls?call=${encodeURIComponent(id)}`,
        });
      }
    }
    return {
      campaign_id: campaignId,
      in_flight: inFlight,
      portal_url: `${this.sm.appUrl}/app/developer?campaign=${encodeURIComponent(campaignId)}`,
      stats: activity.stats ?? null,
    };
  }

  /** One call — while in_progress the transcript grows on each poll. */
  getCall(callId: string): Promise<{ call: Record<string, unknown> }> {
    return this.sm.requestAccountApi("GET", `/api/v1/calls/${encodeURIComponent(callId)}`);
  }

  /** Mint a recipient's tracked tap-to-sign link (inherits the campaign's signing PDF). */
  createSignLink(
    campaignId: string,
    recipientId: string,
    opts: { title?: string; message?: string } = {},
  ): Promise<{ link: Record<string, unknown> }> {
    return this.sm.requestAccountApi(
      "POST",
      `/api/v1/campaigns/${encodeURIComponent(campaignId)}/recipients/${encodeURIComponent(recipientId)}/sign-link`,
      compact({ title: opts.title, message: opts.message }),
    );
  }

  /**
   * Upload the PDF this campaign sends for e-signature. Pass raw bytes
   * (Uint8Array/ArrayBuffer/Blob — in Node: fs.readFileSync(path)). The server
   * auto-detects signature/date/initials lines and returns their placements —
   * apply them with setSignatureFields.
   */
  uploadSigningDocument(
    campaignId: string,
    file: Uint8Array | ArrayBuffer | Blob,
    filename = "document.pdf",
  ): Promise<{ campaign: CampaignSummary; asset: Record<string, unknown>; detected_fields: Record<string, unknown>[] }> {
    return this.sm.requestAccountUpload(
      `/api/v1/campaigns/${encodeURIComponent(campaignId)}/signing/document`,
      file,
      filename,
    );
  }

  detectSignatureFields(campaignId: string): Promise<{ fields: Record<string, unknown>[]; detected: boolean }> {
    return this.sm.requestAccountApi("POST", `/api/v1/campaigns/${encodeURIComponent(campaignId)}/signing/detect-fields`, {});
  }

  /**
   * Place the signing fields: [{key, type: "signature"|"date"|"initials"|"text",
   * label, required, placement: {page, x, y, width, height}}] in PDF points
   * (origin bottom-left, 612x792 page). Merges onto the stored doc config.
   */
  async setSignatureFields(
    campaignId: string,
    fields: Record<string, unknown>[],
  ): Promise<{ campaign: CampaignSummary }> {
    if (!Array.isArray(fields) || !fields.length) {
      throw new SupafoneLabsError("fields must be a non-empty array of placed fields");
    }
    const { campaign } = await this.get(campaignId);
    const settings = { ...((campaign.settings as Record<string, unknown>) ?? {}) };
    const native = { ...((settings.native_signing as Record<string, unknown>) ?? {}) };
    if (!native.pdfUrl && !native.storedName) {
      throw new SupafoneLabsError("Upload the signing PDF first (uploadSigningDocument)");
    }
    native.enabled = true;
    native.fields = fields;
    return this.update(campaignId, { settings: { ...settings, native_signing: native } });
  }

  // -- campaign-as-code (one YAML/JSON document per campaign) ----------------

  /** Pure dry-run: {valid, errors[], warnings[], summary} — no side effects. */
  validateConfig(
    config: string,
    opts: { accountId?: string; launch?: boolean } = {},
  ): Promise<CampaignConfigReport> {
    return this.sm.requestAccountApi("POST", "/api/v1/campaigns/config/validate", {
      config,
      ...compact({ account_id: opts.accountId, launch: opts.launch }),
    });
  }

  /**
   * Upsert a campaign from a campaign-as-code YAML/JSON document (by slug).
   * The doc's branding:/intake_form: blocks restyle the campaign's agent and
   * generate its intake form on apply. launch:true starts REAL calls/emails.
   */
  applyConfig(
    config: string,
    opts: { accountId?: string; launch?: boolean } = {},
  ): Promise<CampaignConfigApplyResult> {
    return this.sm.requestAccountApi("POST", "/api/v1/campaigns/config/apply", {
      config,
      ...compact({ account_id: opts.accountId, launch: opts.launch }),
    });
  }

  /** The campaign as its canonical YAML document — round-trips through applyConfig. */
  exportConfig(campaignId: string): Promise<{ config: string; format: string; slug: string }> {
    return this.sm.requestAccountApi("GET", `/api/v1/campaigns/${encodeURIComponent(campaignId)}/config`);
  }

  /**
   * Draft a campaign-as-code YAML document from a plain-language description
   * (+ optional CSV of leads). No side effects — review, then applyConfig.
   */
  generateConfig(opts: {
    prompt: string;
    csv?: string;
    agentId?: string;
    accountId?: string;
  }): Promise<{ config: string; format: string; recipients_parsed: number; generated: boolean }> {
    if (!opts?.prompt?.trim()) {
      throw new SupafoneLabsError("prompt is required — describe the campaign to draft");
    }
    return this.sm.requestAccountApi("POST", "/api/v1/campaigns/config/generate", {
      prompt: opts.prompt.trim(),
      ...compact({ csv: opts.csv, agent_id: opts.agentId, account_id: opts.accountId }),
    });
  }
}

class LabsNamespace {
  readonly agents: LabsAgentsNamespace;
  readonly presets: LabsPresetsNamespace;
  readonly tools: LabsToolsNamespace;
  readonly voices: LabsVoicesNamespace;
  readonly phoneNumbers: LabsPhoneNumbersNamespace;
  readonly telephony: LabsTelephonyNamespace;
  readonly calls: LabsCallsNamespace;
  readonly recordings: LabsRecordingsNamespace;
  readonly transcripts: LabsTranscriptsNamespace;

  constructor(private sm: SupafoneLabs) {
    this.agents = new LabsAgentsNamespace(sm);
    this.presets = new LabsPresetsNamespace(sm);
    this.tools = new LabsToolsNamespace(sm);
    this.voices = new LabsVoicesNamespace(sm);
    this.phoneNumbers = new LabsPhoneNumbersNamespace(sm);
    this.telephony = new LabsTelephonyNamespace(sm);
    this.calls = new LabsCallsNamespace(sm);
    this.recordings = new LabsRecordingsNamespace(sm);
    this.transcripts = new LabsTranscriptsNamespace(sm);
  }

  /** Discover the Supafone convenience layer over Ultravox. */
  capabilities(): Promise<LabsCapabilitiesResponse> {
    return this.sm.requestSupafoneApi<LabsCapabilitiesResponse>("GET", "/api/v1/labs/capabilities");
  }
}

class LabsAgentsNamespace {
  constructor(private sm: SupafoneLabs) {}

  /** Spawn a durable hosted Supafone agent backed by Ultravox and Supafone-managed providers. */
  create(input: CreateLabsAgentRequest): Promise<CreateLabsAgentResponse> {
    return this.sm.requestSupafoneApi<CreateLabsAgentResponse>(
      "POST",
      "/api/v1/labs/agents",
      labsAgentPayload(this.withVoiceWatcher(input)),
    );
  }

  /** Default the agent onto the client's Voice Watcher setting (live supervision
   * + QA + scoring) unless the caller set it explicitly; mirror into
   * labs.voice_watcher when a labs block exists. Never overwrites a caller value. */
  private withVoiceWatcher(input: CreateLabsAgentRequest): CreateLabsAgentRequest {
    const out: CreateLabsAgentRequest = { ...input };
    if (out.voice_watcher === undefined && out.voiceWatcher === undefined) {
      out.voice_watcher = this.sm.voiceWatcher;
    }
    const labs = out.labs;
    if (labs && labs.voice_watcher === undefined && labs.voiceWatcher === undefined) {
      out.labs = { ...labs, voice_watcher: this.sm.voiceWatcher };
    }
    return out;
  }

  /** Create an inbound receptionist/intake agent. No Twilio account is required. */
  createInbound(input: CreateLabsAgentRequest): Promise<CreateLabsAgentResponse> {
    return this.create({
      ...input,
      style: "inbound",
      direction: "inbound",
      agentType: input.agentType ?? input.agent_type ?? "phone",
      presetKey: input.presetKey ?? input.preset_key ?? "general_intake_receptionist",
      telephony: input.telephony ?? { mode: "supafone_managed", provider: "supafone" },
    });
  }

  /** Create an outbound sales/speed-to-lead/campaign agent. No Twilio account is required. */
  createOutbound(input: CreateLabsAgentRequest): Promise<CreateLabsAgentResponse> {
    return this.create({
      ...input,
      style: "outbound",
      direction: "outbound",
      agentType: input.agentType ?? input.agent_type ?? "campaign",
      presetKey: input.presetKey ?? input.preset_key ?? "speed_to_lead_caller",
      telephony: input.telephony ?? { mode: "supafone_managed", provider: "supafone" },
    });
  }

  /**
   * Create an inbound agent, buy a Supafone-managed phone number, and assign it.
   * This is the zero-Twilio-account happy path.
   */
  async createInboundWithNumber(
    input: CreateLabsAgentWithNumberRequest,
  ): Promise<CreateLabsAgentWithNumberResponse> {
    const agent = await this.createInbound(input);
    const agentKey = String(agent.agent?.agent_key ?? input.agentKey ?? input.agent_key ?? "");
    const number = await new LabsPhoneNumbersNamespace(this.sm).buyAndAssign({
      ...(input.number ?? {}),
      agentKey,
      agentName: input.assistantName ?? input.assistant_name ?? input.name,
      friendlyName: input.number?.friendlyName ?? input.number?.friendly_name ?? input.name,
      style: "inbound",
      presetKey: input.presetKey ?? input.preset_key ?? "general_intake_receptionist",
      telephony: input.number?.telephony ?? { mode: "supafone_managed", provider: "supafone" },
    });
    return { ...agent, number };
  }

  /**
   * Create an outbound agent, buy a Supafone-managed caller ID, and assign it.
   * For sales teams this is the easiest path: Supafone owns telephony setup.
   */
  async createOutboundWithNumber(
    input: CreateLabsAgentWithNumberRequest,
  ): Promise<CreateLabsAgentWithNumberResponse> {
    const agent = await this.createOutbound(input);
    const agentKey = String(agent.agent?.agent_key ?? input.agentKey ?? input.agent_key ?? "");
    const number = await new LabsPhoneNumbersNamespace(this.sm).buyAndAssign({
      ...(input.number ?? {}),
      agentKey,
      agentName: input.assistantName ?? input.assistant_name ?? input.name,
      friendlyName: input.number?.friendlyName ?? input.number?.friendly_name ?? input.name,
      style: "outbound",
      presetKey: input.presetKey ?? input.preset_key ?? "speed_to_lead_caller",
      telephony: input.number?.telephony ?? { mode: "supafone_managed", provider: "supafone" },
    });
    return { ...agent, number };
  }

  /** List durable agents created in the Supafone account tied to this API key. */
  list(opts: ListLabsAgentsOptions = {}): Promise<ListLabsAgentsResponse> {
    const q = new URLSearchParams();
    if (opts.agencyId) q.set("agency_id", opts.agencyId);
    if (opts.agentType) q.set("agent_type", opts.agentType);
    if (opts.style) q.set("style", opts.style);
    const suffix = q.toString() ? `?${q}` : "";
    return this.sm.requestSupafoneApi<ListLabsAgentsResponse>("GET", `/api/v1/labs/agents${suffix}`);
  }

  /** Fetch one durable agent by key. */
  get(agentKey: string, opts: GetLabsAgentOptions = {}): Promise<GetLabsAgentResponse> {
    const q = new URLSearchParams();
    if (opts.agencyId) q.set("agency_id", opts.agencyId);
    if (opts.agentType) q.set("agent_type", opts.agentType);
    const suffix = q.toString() ? `?${q}` : "";
    return this.sm.requestSupafoneApi<GetLabsAgentResponse>(
      "GET",
      `/api/v1/labs/agents/${encodeURIComponent(agentKey)}${suffix}`,
    );
  }

  /** Delete an agent. Optionally ask the backend to release assigned numbers. */
  delete(agentKey: string, opts: DeleteLabsAgentOptions = {}): Promise<DeleteLabsAgentResponse> {
    const q = new URLSearchParams();
    const agencyId = opts.agency_id ?? opts.agencyId;
    const releaseNumbers = opts.release_numbers ?? opts.releaseNumbers;
    if (agencyId) q.set("agency_id", agencyId);
    if (releaseNumbers !== undefined) q.set("release_numbers", String(releaseNumbers));
    const suffix = q.toString() ? `?${q}` : "";
    return this.sm.requestSupafoneApi<DeleteLabsAgentResponse>(
      "DELETE",
      `/api/v1/labs/agents/${encodeURIComponent(agentKey)}${suffix}`,
    );
  }
}

class LabsPresetsNamespace {
  constructor(private sm: SupafoneLabs) {}

  /** Out-of-the-box multistage agent presets. */
  list(): Promise<LabsPresetListResponse> {
    return this.sm.requestSupafoneApi<LabsPresetListResponse>("GET", "/api/v1/labs/presets");
  }
}

class LabsToolsNamespace {
  constructor(private sm: SupafoneLabs) {}

  /** Built-in tools Supafone agents can use. */
  list(): Promise<LabsToolListResponse> {
    return this.sm.requestSupafoneApi<LabsToolListResponse>("GET", "/api/v1/labs/tools");
  }
}

class LabsVoicesNamespace {
  constructor(private sm: SupafoneLabs) {}

  /** Supafone-managed Ultravox, Cartesia, Inworld, and ElevenLabs-compatible voices. */
  list(opts: LabsVoiceListOptions = {}): Promise<LabsVoiceListResponse> {
    const q = new URLSearchParams();
    if (opts.provider) q.set("provider", opts.provider);
    const suffix = q.toString() ? `?${q}` : "";
    return this.sm.requestSupafoneApi<LabsVoiceListResponse>("GET", `/api/v1/labs/voices${suffix}`);
  }
}

class LabsCallsNamespace {
  constructor(private sm: SupafoneLabs) {}

  list(opts: LabsCallListOptions = {}): Promise<LabsCallListResponse> {
    const q = hostedListQuery(opts);
    const suffix = q.toString() ? `?${q}` : "";
    return this.sm.requestSupafoneApi<LabsCallListResponse>("GET", `/api/v1/labs/calls${suffix}`);
  }

  get(callId: string, opts: { agencyId?: string } = {}): Promise<Record<string, unknown>> {
    const q = new URLSearchParams();
    if (opts.agencyId) q.set("agency_id", opts.agencyId);
    const suffix = q.toString() ? `?${q}` : "";
    return this.sm.requestSupafoneApi("GET", `/api/v1/labs/calls/${encodeURIComponent(callId)}${suffix}`);
  }
}

class LabsRecordingsNamespace {
  constructor(private sm: SupafoneLabs) {}

  list(opts: LabsRecordingListOptions = {}): Promise<LabsRecordingListResponse> {
    const q = hostedListQuery(opts);
    const callId = opts.call_id ?? opts.callId;
    if (callId) q.set("call_id", callId);
    const suffix = q.toString() ? `?${q}` : "";
    return this.sm.requestSupafoneApi<LabsRecordingListResponse>("GET", `/api/v1/labs/recordings${suffix}`);
  }

  get(recordingId: string, opts: { agencyId?: string } = {}): Promise<Record<string, unknown>> {
    const q = new URLSearchParams();
    if (opts.agencyId) q.set("agency_id", opts.agencyId);
    const suffix = q.toString() ? `?${q}` : "";
    return this.sm.requestSupafoneApi("GET", `/api/v1/labs/recordings/${encodeURIComponent(recordingId)}${suffix}`);
  }

  delete(recordingId: string, opts: { agencyId?: string; reason?: string } = {}): Promise<Record<string, unknown>> {
    const q = new URLSearchParams();
    if (opts.agencyId) q.set("agency_id", opts.agencyId);
    if (opts.reason) q.set("reason", opts.reason);
    const suffix = q.toString() ? `?${q}` : "";
    return this.sm.requestSupafoneApi("DELETE", `/api/v1/labs/recordings/${encodeURIComponent(recordingId)}${suffix}`);
  }
}

class LabsTranscriptsNamespace {
  constructor(private sm: SupafoneLabs) {}

  list(opts: LabsTranscriptListOptions = {}): Promise<LabsTranscriptListResponse> {
    const q = hostedListQuery(opts);
    const callId = opts.call_id ?? opts.callId;
    if (callId) q.set("call_id", callId);
    const suffix = q.toString() ? `?${q}` : "";
    return this.sm.requestSupafoneApi<LabsTranscriptListResponse>("GET", `/api/v1/labs/transcripts${suffix}`);
  }

  get(transcriptId: string, opts: { agencyId?: string } = {}): Promise<Record<string, unknown>> {
    const q = new URLSearchParams();
    if (opts.agencyId) q.set("agency_id", opts.agencyId);
    const suffix = q.toString() ? `?${q}` : "";
    return this.sm.requestSupafoneApi("GET", `/api/v1/labs/transcripts/${encodeURIComponent(transcriptId)}${suffix}`);
  }
}

class LabsPhoneNumbersNamespace {
  constructor(private sm: SupafoneLabs) {}

  /** List numbers already owned by this Supafone account. */
  list(opts: LabsPhoneNumberListOptions = {}): Promise<LabsPhoneNumberListResponse> {
    const q = new URLSearchParams();
    if (opts.agencyId) q.set("agency_id", opts.agencyId);
    if (opts.activeOnly !== undefined) q.set("active_only", String(opts.activeOnly));
    const suffix = q.toString() ? `?${q}` : "";
    return this.sm.requestSupafoneApi<LabsPhoneNumberListResponse>(
      "GET",
      `/api/v1/labs/phone-numbers${suffix}`,
    );
  }

  /** Search Supafone-managed inventory. This uses Supafone's master telephony account. */
  search(opts: LabsPhoneNumberSearchOptions = {}): Promise<LabsPhoneNumberSearchResponse> {
    return this.sm.requestSupafoneApi<LabsPhoneNumberSearchResponse>(
      "POST",
      "/api/v1/labs/phone-numbers/search",
      phoneNumberSearchPayload(opts),
    );
  }

  /** Buy a Supafone-managed number. Developers do not need a Twilio account. */
  buy(input: LabsPhoneNumberProvisionRequest): Promise<LabsPhoneNumberProvisionResponse> {
    return this.sm.requestSupafoneApi<LabsPhoneNumberProvisionResponse>(
      "POST",
      "/api/v1/labs/phone-numbers",
      phoneNumberProvisionPayload({
        ...input,
        telephony: input.telephony ?? { mode: "supafone_managed", provider: "supafone" },
      }),
    );
  }

  /** Attach an existing Supafone number to an inbound or outbound agent. */
  assign(numberId: string, input: LabsPhoneNumberAssignRequest = {}): Promise<LabsPhoneNumberAssignResponse> {
    return this.sm.requestSupafoneApi<LabsPhoneNumberAssignResponse>(
      "POST",
      `/api/v1/labs/phone-numbers/${encodeURIComponent(numberId)}/assign`,
      phoneNumberAssignPayload(input),
    );
  }

  /** Unassign a number from an agent but keep it reserved on the account. */
  unassign(numberId: string, input: LabsPhoneNumberReleaseRequest = {}): Promise<LabsPhoneNumberReleaseResponse> {
    return this.sm.requestSupafoneApi<LabsPhoneNumberReleaseResponse>(
      "POST",
      `/api/v1/labs/phone-numbers/${encodeURIComponent(numberId)}/unassign`,
      phoneNumberReleasePayload(input),
    );
  }

  /** Give a number back to the shared pool or release the reservation. */
  release(numberId: string, input: LabsPhoneNumberReleaseRequest = {}): Promise<LabsPhoneNumberReleaseResponse> {
    return this.sm.requestSupafoneApi<LabsPhoneNumberReleaseResponse>(
      "POST",
      `/api/v1/labs/phone-numbers/${encodeURIComponent(numberId)}/release`,
      phoneNumberReleasePayload({ ...input, returnToPool: input.returnToPool ?? input.return_to_pool ?? true }),
    );
  }

  /** Alias for release(numberId, { returnToPool: true }). */
  returnToPool(numberId: string, input: LabsPhoneNumberReleaseRequest = {}): Promise<LabsPhoneNumberReleaseResponse> {
    return this.release(numberId, { ...input, returnToPool: true });
  }

  /** Delete/release a number reservation. Backend policy decides whether this is allowed. */
  delete(numberId: string, input: LabsPhoneNumberReleaseRequest = {}): Promise<LabsPhoneNumberReleaseResponse> {
    const q = new URLSearchParams();
    const agencyId = input.agency_id ?? input.agencyId;
    if (agencyId) q.set("agency_id", agencyId);
    const suffix = q.toString() ? `?${q}` : "";
    return this.sm.requestSupafoneApi<LabsPhoneNumberReleaseResponse>(
      "DELETE",
      `/api/v1/labs/phone-numbers/${encodeURIComponent(numberId)}${suffix}`,
      phoneNumberReleasePayload(input),
    );
  }

  /**
   * Search if needed, buy the first matching Supafone-managed number, and assign
   * it to the supplied agent. This is the zero-Twilio-account happy path.
   */
  async buyAndAssign(input: LabsPhoneNumberBuyAndAssignRequest): Promise<LabsPhoneNumberProvisionResponse> {
    let phoneNumber = input.phoneNumber ?? input.phone_number ?? "";
    if (!phoneNumber) {
      const found = await this.search({
        ...(input.search ?? {}),
        agencyId: input.agencyId ?? input.agency_id ?? input.search?.agencyId,
        limit: input.search?.limit ?? 1,
      });
      phoneNumber = found.numbers[0]?.phone_number ?? "";
      if (!phoneNumber) {
        throw new SupafoneLabsError("No Supafone-managed phone numbers matched the search");
      }
    }
    return this.buy({
      ...input,
      phoneNumber,
      telephony: input.telephony ?? { mode: "supafone_managed", provider: "supafone" },
    });
  }
}

class LabsTelephonyNamespace {
  constructor(private sm: SupafoneLabs) {}

  /** Read the account telephony contract. Defaults to Supafone-managed. */
  get(opts: { agencyId?: string } = {}): Promise<LabsTelephonyResponse> {
    const q = new URLSearchParams();
    if (opts.agencyId) q.set("agency_id", opts.agencyId);
    const suffix = q.toString() ? `?${q}` : "";
    return this.sm.requestSupafoneApi<LabsTelephonyResponse>("GET", `/api/v1/labs/telephony${suffix}`);
  }

  /** Configure advanced BYOK telephony, or reset back to Supafone-managed. */
  configure(input: LabsTelephonyConfig): Promise<LabsTelephonyConfigureResponse> {
    return this.sm.requestSupafoneApi<LabsTelephonyConfigureResponse>(
      "PUT",
      "/api/v1/labs/telephony",
      telephonyPayload(input),
    );
  }

  /** Reset to the seamless default where Supafone buys and routes numbers. */
  useSupafoneManaged(agencyId?: string): Promise<LabsTelephonyConfigureResponse> {
    return this.configure({ agencyId, mode: "supafone_managed", provider: "supafone" });
  }
}

/**
 * The agent builder. These methods are account/session-scoped — call
 * `login(email, password)` first, or the gateway returns 401 "Log in first".
 */
class BuilderNamespace {
  constructor(private sm: SupafoneLabs) {}
  /** One supervised builder turn: whisper + guided agent reply. */
  chat(sessionId: string, messages: BuilderTurn[]): Promise<BuilderChatResult> {
    return this.sm.request<BuilderChatResult>(
      "POST",
      "/v1/builder/chat",
      { session_id: sessionId, messages },
      true,
    );
  }
  /** End a test call: grades it and files a report for the optimizer. */
  finish(
    sessionId: string,
    messages: BuilderTurn[],
  ): Promise<{ score: number; outcome: string; summary: string }> {
    return this.sm.request("POST", "/v1/builder/finish", { session_id: sessionId, messages }, true);
  }
  config(): Promise<unknown> {
    return this.sm.request("GET", "/v1/builder/config", undefined, true);
  }
  saveConfig(config: unknown): Promise<unknown> {
    return this.sm.request("POST", "/v1/builder/config", config, true);
  }
}

class QANamespace {
  constructor(private sm: SupafoneLabs) {}
  /**
   * Run the adversarial QA suite, A/B (supervised vs unsupervised).
   * Session-scoped — call login() first.
   */
  run(opts: { scenarios?: string[]; turns?: number } = {}): Promise<QAResult> {
    return this.sm.request<QAResult>(
      "POST",
      "/v1/qa/run",
      { scenarios: opts.scenarios ?? [], turns: opts.turns ?? 2 },
      true,
    );
  }
  /**
   * Auto-generate adversarial test scenarios from the agent's own prompt
   * (key-scoped). Each scenario carries a persona, an opener, and the one
   * assertion the agent must (or must not) satisfy.
   */
  generate(opts: { agentPrompt: string; count?: number }): Promise<{ scenarios: QAScenario[] }> {
    return this.sm.request("POST", "/v1/qa/generate", {
      agent_prompt: opts.agentPrompt,
      count: opts.count ?? 5,
    });
  }
  /**
   * Build + run a bespoke adversarial suite in one call: scenarios are
   * generated from the agent's own objective, each is played as a mock call
   * against the REAL configured agent, and every call is judged twice —
   * pass/fail on the scenario's assertion AND an SSR grade (poorly/ok/good/
   * great/perfectly) against the objective. Session-scoped — login() first.
   */
  suite(opts: { count?: number; turns?: number; supervised?: boolean } = {}): Promise<QASuiteResult> {
    return this.sm.request<QASuiteResult>(
      "POST",
      "/v1/qa/suite",
      {
        count: opts.count ?? 4,
        turns: opts.turns ?? 2,
        supervised: opts.supervised ?? false,
      },
      true,
    );
  }
  /** Past QA runs (works with the API key). */
  history(agent = "builder", limit = 40): Promise<unknown> {
    return this.sm.request("GET", `/v1/qa/runs?agent=${encodeURIComponent(agent)}&limit=${limit}`);
  }
}

class OptimizerNamespace {
  constructor(private sm: SupafoneLabs) {}
  /** Improve the standing directive from accumulated call reports (OPRO-style). */
  improve(agent = "builder"): Promise<{ version: number; text: string; rationale: string }> {
    return this.sm.request("POST", "/v1/optimizer/improve", { agent });
  }
  /** Fetch the current standing directive. */
  standing(agent = "builder"): Promise<{ version: number; text: string }> {
    return this.sm.request("GET", `/v1/optimizer/standing?agent=${encodeURIComponent(agent)}`);
  }
  /** List the post-call reports behind the optimizer. */
  reports(agent = "builder", limit = 40): Promise<{ reports: unknown[] }> {
    return this.sm.request(
      "GET",
      `/v1/optimizer/reports?agent=${encodeURIComponent(agent)}&limit=${limit}`,
    );
  }
}

function labsAgentPayload(input: CreateLabsAgentRequest): Record<string, unknown> {
  return compact({
    agency_id: input.agency_id ?? input.agencyId,
    agent_key: input.agent_key ?? input.agentKey,
    agent_type: input.agent_type ?? input.agentType,
    style: input.agent_style ?? input.agentStyle ?? input.style,
    name: input.name,
    assistant_name: input.assistant_name ?? input.assistantName,
    business_name: input.business_name ?? input.businessName,
    industry: input.industry,
    website_url: input.website_url ?? input.websiteUrl,
    phone_number: input.phone_number ?? input.phoneNumber,
    number_strategy: input.number_strategy ?? input.numberStrategy,
    number_pool: input.number_pool ?? input.numberPool,
    premium: input.premium,
    direction: input.direction,
    preset_key: input.preset_key ?? input.presetKey,
    runtime_mode: input.runtime_mode ?? input.runtimeMode,
    call_stages: callStagesPayload(input),
    goal: input.goal,
    greeting: input.greeting,
    system_prompt: input.system_prompt ?? input.systemPrompt,
    language: input.language,
    voice: input.voice ? voicePayload(input.voice) : undefined,
    provider_keys: input.provider_keys ?? (input.providerKeys ? providerKeysPayload(input.providerKeys) : undefined),
    byok: input.byok ? byokPayload(input.byok) : undefined,
    telephony: input.telephony ? telephonyPayload(input.telephony) : undefined,
    custom_sip: customSipPayload(input.custom_sip ?? input.customSip ?? input.sip),
    recording: input.recording ? recordingPayload(input.recording) : undefined,
    transcription: input.transcription ? transcriptionPayload(input.transcription) : undefined,
    artifacts: input.artifacts ? artifactsPayload(input.artifacts) : undefined,
    compliance: input.compliance,
    tools: input.tools ? toolsPayload(input.tools) : undefined,
    labs: input.labs ? labsPayload(input.labs) : undefined,
    ultravox: input.ultravox ? ultravoxPayload(input.ultravox) : undefined,
    voice_watcher: input.voice_watcher ?? input.voiceWatcher,
    voice_watcher_model: input.voice_watcher_model ?? input.voiceWatcherModel,
    metadata: input.metadata,
  });
}

function hostedListQuery(opts: LabsCallListOptions): URLSearchParams {
  const q = new URLSearchParams();
  if (opts.agencyId) q.set("agency_id", opts.agencyId);
  const agentKey = opts.agent_key ?? opts.agentKey;
  if (agentKey) q.set("agent_key", agentKey);
  if (opts.limit !== undefined) q.set("limit", String(opts.limit));
  return q;
}

function telephonyPayload(input: LabsTelephonyConfig): Record<string, unknown> {
  return compact({
    agency_id: input.agency_id ?? input.agencyId,
    mode: input.mode,
    provider: input.provider,
    number_strategy: input.number_strategy ?? input.numberStrategy,
    number_pool: input.number_pool ?? input.numberPool,
    number_id: input.number_id ?? input.numberId,
    premium: input.premium,
    label: input.label,
    credentials: input.credentials ? telephonyCredentialsPayload(input.credentials) : undefined,
    provider_settings: input.provider_settings ?? input.providerSettings,
    custom_sip: customSipPayload(input.custom_sip ?? input.customSip),
    metadata: input.metadata,
  });
}

function telephonyCredentialsPayload(input: LabsTelephonyCredentials): Record<string, unknown> {
  return compact({
    account_sid: input.account_sid ?? input.accountSid,
    auth_token: input.auth_token ?? input.authToken,
    api_key: input.api_key ?? input.apiKey,
    api_secret: input.api_secret ?? input.apiSecret,
    auth_id: input.auth_id ?? input.authId,
    connection_id: input.connection_id ?? input.connectionId,
    from_number: input.from_number ?? input.fromNumber,
    sip_trunk_uri: input.sip_trunk_uri ?? input.sipTrunkUri,
    sip_host: input.sip_host ?? input.sipHost,
    username: input.username,
    password: input.password,
    webhook_secret: input.webhook_secret ?? input.webhookSecret,
    telnyx_connection_id: input.telnyx_connection_id ?? input.telnyxConnectionId,
    signalwire_space_url: input.signalwire_space_url ?? input.signalwireSpaceUrl,
    project_id: input.project_id ?? input.projectId,
    application_id: input.application_id ?? input.applicationId,
    trunk_id: input.trunk_id ?? input.trunkId,
    endpoint_id: input.endpoint_id ?? input.endpointId,
    token: input.token,
    secret: input.secret,
    custom_sip: customSipPayload(input.custom_sip ?? input.customSip),
  });
}

function phoneNumberSearchPayload(input: LabsPhoneNumberSearchOptions): Record<string, unknown> {
  return compact({
    agency_id: input.agency_id ?? input.agencyId,
    number_pool: input.number_pool ?? input.numberPool,
    number_strategy: input.number_strategy ?? input.numberStrategy,
    country_code: input.country_code ?? input.countryCode,
    area_code: input.area_code ?? input.areaCode,
    postal_code: input.postal_code ?? input.postalCode,
    zip_code: input.zip_code ?? input.zipCode,
    contains: input.contains,
    number_type: input.number_type ?? input.numberType,
    limit: input.limit,
    capabilities: input.capabilities,
  });
}

function phoneNumberProvisionPayload(input: LabsPhoneNumberProvisionRequest): Record<string, unknown> {
  return compact({
    agency_id: input.agency_id ?? input.agencyId,
    phone_number: input.phone_number ?? input.phoneNumber,
    friendly_name: input.friendly_name ?? input.friendlyName,
    department_id: input.department_id ?? input.departmentId,
    agent_key: input.agent_key ?? input.agentKey,
    agent_id: input.agent_id ?? input.agentId,
    agent_name: input.agent_name ?? input.agentName,
    preset_key: input.preset_key ?? input.presetKey,
    number_strategy: input.number_strategy ?? input.numberStrategy,
    number_pool: input.number_pool ?? input.numberPool,
    premium: input.premium,
    style: input.agent_style ?? input.agentStyle ?? input.style,
    direction: input.direction,
    telephony: input.telephony ? telephonyPayload(input.telephony) : undefined,
    metadata: input.metadata,
  });
}

function phoneNumberAssignPayload(input: LabsPhoneNumberAssignRequest): Record<string, unknown> {
  return compact({
    agency_id: input.agency_id ?? input.agencyId,
    agent_key: input.agent_key ?? input.agentKey,
    agent_id: input.agent_id ?? input.agentId,
    agent_name: input.agent_name ?? input.agentName,
    friendly_name: input.friendly_name ?? input.friendlyName,
    preset_key: input.preset_key ?? input.presetKey,
    number_strategy: input.number_strategy ?? input.numberStrategy,
    number_pool: input.number_pool ?? input.numberPool,
    premium: input.premium,
    style: input.agent_style ?? input.agentStyle ?? input.style,
    direction: input.direction,
    telephony: input.telephony ? telephonyPayload(input.telephony) : undefined,
    metadata: input.metadata,
  });
}

function phoneNumberReleasePayload(input: LabsPhoneNumberReleaseRequest): Record<string, unknown> {
  return compact({
    agency_id: input.agency_id ?? input.agencyId,
    reason: input.reason,
    return_to_pool: input.return_to_pool ?? input.returnToPool,
    metadata: input.metadata,
  });
}

function callStagesPayload(input: CreateLabsAgentRequest): Record<string, unknown>[] | undefined {
  const explicit = input.call_stages ?? input.callStages ?? input.stages;
  const auto = input.auto_call_stages ?? input.autoCallStages;
  if (Array.isArray(explicit)) return explicit.map(callStagePayload);
  if (explicit === false || auto === false) return undefined;
  return generateCallStages(input).map(callStagePayload);
}

function callStagePayload(input: LabsCallStage): Record<string, unknown> {
  return compact({
    key: input.key ?? input.id,
    name: input.name,
    goal: input.goal,
    instructions: input.instructions,
    exit_criteria: input.exit_criteria ?? input.exitCriteria,
    tools: input.tools,
    metadata: input.metadata,
  });
}

export function generateCallStages(input: CreateLabsAgentRequest): LabsCallStage[] {
  const direction = String(input.direction ?? input.agent_style ?? input.agentStyle ?? input.style ?? "inbound").toLowerCase();
  const haystack = [
    input.name,
    input.assistant_name ?? input.assistantName,
    input.business_name ?? input.businessName,
    input.industry,
    input.goal,
    input.system_prompt ?? input.systemPrompt,
    input.preset_key ?? input.presetKey,
  ].filter(Boolean).join(" ").toLowerCase();
  const meta = { auto_generated: true, source: "supafone-labs-sdk" };

  if (direction === "outbound" || haystack.includes("sales") || haystack.includes("lead")) {
    return [
      stage("intro_consent", "Intro and consent", "State who you are, why you are calling, and offer an immediate opt-out.", ["Caller understands purpose", "Opt-out is honored"], meta),
      stage("qualification", "Qualification", "Confirm fit, urgency, decision process, and the best next step.", ["Need and timeline are clear"], meta),
      stage("offer", "Offer", "Explain the next step in plain language without unsupported claims.", ["Caller understands the next step"], meta),
      stage("booking", "Booking", "Book or route the caller only after confirming required details.", ["Next step is confirmed by a tool or human handoff"], meta),
      stage("close", "Close", "Summarize what will happen next and end politely.", ["Caller knows the follow-up path"], meta),
    ];
  }

  if (haystack.includes("legal") || haystack.includes("law") || haystack.includes("injury") || haystack.includes("intake")) {
    return [
      stage("greeting", "Greeting", "Open warmly and acknowledge the caller before logistics.", ["Caller need is understood"], meta),
      stage("incident", "Incident details", "Collect what happened, when it happened, injuries, insurance, and contact details.", ["Core facts are collected"], meta),
      stage("screening", "Screening", "Identify urgency, jurisdiction, conflicts, and whether human escalation is required.", ["Escalation decision is clear"], meta),
      stage("booking", "Consult booking", "Book the right next step without quoting fees or inventing availability.", ["Booking or handoff is tool-confirmed"], meta),
      stage("close", "Close", "Summarize the next step and set expectations accurately.", ["Caller knows exactly what happens next"], meta),
    ];
  }

  if (haystack.includes("medical") || haystack.includes("clinic") || haystack.includes("patient") || haystack.includes("health")) {
    return [
      stage("greeting", "Greeting", "Identify the caller need and keep the tone calm and concise.", ["Caller need is understood"], meta),
      stage("patient_context", "Patient context", "Collect non-sensitive scheduling context and avoid medical advice.", ["Required scheduling context is collected"], meta),
      stage("routing", "Routing", "Route urgent, billing, clinical, and scheduling requests correctly.", ["Correct route is selected"], meta),
      stage("appointment", "Appointment", "Book or request the appointment only after confirming details.", ["Appointment path is confirmed"], meta),
      stage("close", "Close", "Recap next steps and any confirmed timing.", ["Caller knows the next step"], meta),
    ];
  }

  return [
    stage("greeting", "Greeting", "Open naturally, identify the caller need, and set a helpful tone.", ["Caller need is understood"], meta),
    stage("discovery", "Discovery", "Ask one question at a time until the key details are clear.", ["Required details are collected"], meta),
    stage("resolution", "Resolution", "Answer approved questions or route to the right workflow.", ["Resolution path is selected"], meta),
    stage("action", "Action", "Use tools for booking, routing, messaging, or handoff before claiming success.", ["Action is confirmed by a tool or handoff"], meta),
    stage("close", "Close", "Summarize the outcome and next step accurately.", ["Caller knows what happens next"], meta),
  ];
}

function stage(
  key: string,
  name: string,
  instructions: string,
  exitCriteria: string[],
  metadata: Record<string, unknown>,
): LabsCallStage {
  return {
    key,
    name,
    instructions,
    exitCriteria,
    metadata,
  };
}

function voicePayload(input: LabsVoiceSelection): Record<string, unknown> {
  return compact({
    provider: input.provider,
    voice_id: input.voice_id ?? input.voiceId,
    model: input.model,
  });
}

function providerKeysPayload(input: LabsProviderKeys): Record<string, unknown> {
  return compact({
    ultravox: input.ultravox,
    ultravox_api_key: input.ultravox_api_key ?? input.ultravoxApiKey,
    retell: input.retell,
    retell_api_key: input.retell_api_key ?? input.retellApiKey,
    vapi: input.vapi,
    vapi_api_key: input.vapi_api_key ?? input.vapiApiKey,
    bland: input.bland,
    bland_api_key: input.bland_api_key ?? input.blandApiKey,
    livekit: input.livekit,
    livekit_api_key: input.livekit_api_key ?? input.livekitApiKey,
    livekit_api_secret: input.livekit_api_secret ?? input.livekitApiSecret,
    pipecat: input.pipecat,
    pipecat_api_key: input.pipecat_api_key ?? input.pipecatApiKey,
    twilio: input.twilio,
    twilio_account_sid: input.twilio_account_sid ?? input.twilioAccountSid,
    twilio_auth_token: input.twilio_auth_token ?? input.twilioAuthToken,
    twilio_api_key_sid: input.twilio_api_key_sid ?? input.twilioApiKeySid,
    twilio_api_key_secret: input.twilio_api_key_secret ?? input.twilioApiKeySecret,
    telnyx: input.telnyx,
    telnyx_api_key: input.telnyx_api_key ?? input.telnyxApiKey,
    plivo: input.plivo,
    plivo_auth_id: input.plivo_auth_id ?? input.plivoAuthId,
    plivo_auth_token: input.plivo_auth_token ?? input.plivoAuthToken,
    signalwire: input.signalwire,
    signalwire_api_token: input.signalwire_api_token ?? input.signalwireApiToken,
    signalwire_project_id: input.signalwire_project_id ?? input.signalwireProjectId,
    elevenlabs: input.elevenlabs,
    elevenlabs_api_key: input.elevenlabs_api_key ?? input.elevenlabsApiKey,
    cartesia: input.cartesia,
    cartesia_api_key: input.cartesia_api_key ?? input.cartesiaApiKey,
    inworld: input.inworld,
    inworld_api_key: input.inworld_api_key ?? input.inworldApiKey,
    deepgram: input.deepgram,
    deepgram_api_key: input.deepgram_api_key ?? input.deepgramApiKey,
    anthropic: input.anthropic,
    anthropic_api_key: input.anthropic_api_key ?? input.anthropicApiKey,
    openai: input.openai,
    openai_api_key: input.openai_api_key ?? input.openaiApiKey,
    xai: input.xai,
    xai_api_key: input.xai_api_key ?? input.xaiApiKey,
  });
}

function byokPayload(input: LabsProviderKeys | LabsByokConfig): Record<string, unknown> {
  const structured = input as LabsByokConfig;
  if (
    structured.agentProvider ||
    structured.agent_provider ||
    structured.runtime ||
    structured.telephony ||
    structured.tts ||
    structured.stt ||
    structured.llm ||
    structured.providerKeys ||
    structured.provider_keys ||
    structured.customSip ||
    structured.custom_sip ||
    structured.sip
  ) {
    return compact({
      provider_keys: providerKeysPayload(structured.provider_keys ?? structured.providerKeys ?? {}),
      agent_provider: providerConfigPayload(structured.agent_provider ?? structured.agentProvider ?? structured.runtime),
      // Native (BYOK) Ultravox runtime key — forwarded verbatim so
      // byok.ultravox = {api_key, base_url?} round-trips even when the block
      // also carries an agentProvider / telephony / *tts etc.
      ultravox: structured.ultravox,
      telephony: structured.telephony ? telephonyPayload(structured.telephony) : undefined,
      tts: providerConfigPayload(structured.tts),
      stt: providerConfigPayload(structured.stt),
      llm: providerConfigPayload(structured.llm),
      custom_sip: customSipPayload(structured.custom_sip ?? structured.customSip ?? structured.sip),
    });
  }
  return providerKeysPayload(input as LabsProviderKeys);
}

function providerConfigPayload(input?: LabsProviderByokConfig): Record<string, unknown> | undefined {
  if (!input) return undefined;
  const out: Record<string, unknown> = { ...input };
  delete out.apiKey;
  delete out.api_key;
  delete out.voiceId;
  delete out.voice_id;
  return compact({
    ...out,
    provider: input.provider,
    api_key: input.api_key ?? input.apiKey,
    credentials: input.credentials,
    settings: input.settings,
    model: input.model,
    voice_id: input.voice_id ?? input.voiceId,
  });
}

function toolsPayload(input: LabsToolsConfig): Record<string, unknown> {
  return compact({
    call_routing: input.call_routing ?? input.callRouting,
    scheduling: input.scheduling,
    sms: input.sms,
    email: input.email,
    intake_forms: input.intake_forms ?? input.intakeForms,
    firm_knowledge: input.firm_knowledge ?? input.firmKnowledge,
    existing_client_lookup: input.existing_client_lookup ?? input.existingClientLookup,
    voicemail: input.voicemail,
    emergency_escalation: input.emergency_escalation ?? input.emergencyEscalation,
    custom_tools: input.custom_tools ?? input.customTools,
  });
}

function recordingPayload(input: LabsRecordingConfig): Record<string, unknown> {
  return compact({
    enabled: input.enabled,
    record_audio: input.record_audio ?? input.recordAudio,
    consent_required: input.consent_required ?? input.consentRequired,
    announcement: input.announcement,
    retention_days: input.retention_days ?? input.retentionDays,
    storage: input.storage,
    redact_pii: input.redact_pii ?? input.redactPii,
    metadata: input.metadata,
  });
}

function transcriptionPayload(input: LabsTranscriptionConfig): Record<string, unknown> {
  return compact({
    enabled: input.enabled,
    provider: input.provider,
    model: input.model,
    language: input.language,
    redact_pii: input.redact_pii ?? input.redactPii,
    diarization: input.diarization,
    timestamps: input.timestamps,
    metadata: input.metadata,
  });
}

function artifactsPayload(input: LabsArtifactsConfig): Record<string, unknown> {
  return compact({
    recordings: input.recordings,
    transcripts: input.transcripts,
    summaries: input.summaries,
    qa_reports: input.qa_reports ?? input.qaReports,
    logs: input.logs,
    webhooks: input.webhooks,
    retention_days: input.retention_days ?? input.retentionDays,
    metadata: input.metadata,
  });
}

function labsPayload(input: LabsWatcherConfig): Record<string, unknown> {
  return compact({
    enabled: input.enabled,
    voice_watcher: input.voice_watcher ?? input.voiceWatcher,
    api_key: input.api_key ?? input.apiKey,
    model: input.model,
    mode: input.mode,
    managed_infrastructure: input.managed_infrastructure ?? input.managedInfrastructure,
    stt: input.stt,
    llm: input.llm,
    tts: input.tts,
    provider_keys: input.provider_keys ?? input.providerKeys,
    label: input.label,
  });
}

function ultravoxPayload(input: LabsUltravoxRuntime): Record<string, unknown> {
  return compact({
    model: input.model,
    temperature: input.temperature,
    medium: input.medium,
    vadSettings: input.vadSettings ?? input.vad_settings,
    speaker_first: input.speaker_first ?? input.speakerFirst,
    firstSpeaker: input.firstSpeaker ?? input.first_speaker,
    firstSpeakerSettings: input.firstSpeakerSettings ?? input.first_speaker_settings,
    selectedTools: input.selectedTools ?? input.selected_tools,
    initialMessages: input.initialMessages ?? input.initial_messages,
    initialState: input.initialState ?? input.initial_state,
    initialOutputMedium: input.initialOutputMedium ?? input.initial_output_medium,
    joinTimeout: input.joinTimeout ?? input.join_timeout,
    maxDuration: input.maxDuration ?? input.max_duration,
    max_duration_seconds: input.max_duration_seconds ?? input.maxDurationSeconds,
    timeExceededMessage: input.timeExceededMessage ?? input.time_exceeded_message,
    inactivityMessages: input.inactivityMessages ?? input.inactivity_messages,
    dataConnection: input.dataConnection ?? input.data_connection,
    callbacks: input.callbacks,
    metadata: input.metadata,
    experimentalSettings: input.experimentalSettings ?? input.experimental_settings,
    voiceOverrides: input.voiceOverrides ?? input.voice_overrides,
    retentionPolicy: input.retentionPolicy ?? input.retention_policy,
    callTemplate: input.callTemplate ?? input.call_template,
    custom_sip: customSipPayload(input.custom_sip ?? input.customSip ?? input.sip),
  });
}

function customSipPayload(input?: LabsCustomSipConfig): Record<string, unknown> | undefined {
  if (!input) return undefined;
  return compact({
    sip_trunk_uri: input.sip_trunk_uri ?? input.sipTrunkUri,
    trunk_uri: input.trunk_uri ?? input.trunkUri,
    sip_host: input.sip_host ?? input.sipHost,
    from_number: input.from_number ?? input.fromNumber,
    username: input.username,
    password: input.password,
    transport: input.transport,
    headers: input.headers,
    codecs: input.codecs,
    dtmf_mode: input.dtmf_mode ?? input.dtmfMode,
    metadata: input.metadata,
  });
}

function compact(input: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(input)) {
    if (value !== undefined) out[key] = value;
  }
  return out;
}

function parseSseLog(raw: string): LabsLogEntry | null {
  const data: string[] = [];
  for (const line of raw.split(/\r?\n/)) {
    if (!line || line.startsWith(":")) continue;
    if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  if (!data.length) return null;
  const parsed = safeJson(data.join("\n"));
  if (!parsed || typeof parsed !== "object") return null;
  return parsed as LabsLogEntry;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

export { SupafoneLabs as Supafone };

export default SupafoneLabs;
