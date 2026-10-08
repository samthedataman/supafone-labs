import type { LabsRealtimeSelection, SupafoneLabs } from './index.js';
import { SupafoneVoice } from './voice.js';
import { SupafoneS2S, UltravoxS2S, type S2SProviderName } from './s2s.js';

export type VoiceLayer = 'stt' | 'llm' | 'tts';
export type VoiceCredentialMode = 'auto' | 'managed' | 'byok';
export interface PipelineComponent {
  provider: string;
  model: string;
  voice?: string;
  profile?: string;
  options?: Record<string, unknown>;
}
export interface PipelineConfig {
  schema_version?: 1;
  stt: PipelineComponent;
  llm: PipelineComponent;
  tts: PipelineComponent;
  credentials?: Partial<Record<'default' | VoiceLayer, VoiceCredentialMode>>;
  language?: string;
  region?: string;
  transport?: string;
}
export type VoiceRoute =
  | { kind: 'pipeline'; pipeline: PipelineConfig }
  | { kind: 's2s'; provider: S2SProviderName; model?: string; voice?: string }
  | { kind: 'hybrid'; provider?: 'ultravox' };
export interface VoiceContext { language?: string; region?: string; transport?: string; requires_tools?: boolean; [key: string]: unknown }
export interface VoiceSelection { pipeline?: PipelineConfig | null; realtime?: LabsRealtimeSelection | null }
export interface VoiceCombinationsOptions {
  agency_id?: string;
  context?: VoiceContext;
  filters?: Partial<Record<VoiceLayer, string[]>>;
  offset?: number;
  limit?: number;
}
export interface VoiceCombinationsResponse {
  registry_version: string;
  registry_hash: string;
  counts: Record<string, number>;
  combinations: Array<Record<string, unknown>>;
  next_offset: number | null;
}
const layers: VoiceLayer[] = ['stt', 'llm', 'tts'];
const isObject = (value: unknown): value is Record<string, unknown> =>
  !!value && typeof value === 'object' && !Array.isArray(value);
const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value));
function rejectSecrets(value: unknown) {
  if (Array.isArray(value)) { value.forEach(rejectSecrets); return; }
  if (!isObject(value)) return;
  for (const [key, item] of Object.entries(value)) {
    const normalized = key.replace(/[_-]/g, '').toLowerCase();
    if (['apikey', 'key', 'secret', 'token', 'password', 'authorization', 'credentials', 'accesskeyid', 'secretaccesskey', 'privatekey', 'clientsecret', 'sessiontoken'].includes(normalized) || /(apikey|password|privatekey|clientsecret|accesstoken)$/.test(normalized)) {
      throw new Error('Pipeline configuration accepts profile references, never credentials or secrets');
    }
    rejectSecrets(item);
  }
}
/** Structural checks only. The server is authoritative for model eligibility/readiness. */
export function normalizePipeline(config: PipelineConfig): PipelineConfig {
  if (!isObject(config)) throw new Error('pipeline must be an object');
  if (Object.keys(config).some(k => !['schema_version', ...layers, 'credentials', 'language', 'region', 'transport'].includes(k))) throw new Error('Unknown pipeline field');
  if (config.schema_version !== undefined && config.schema_version !== 1) throw new Error('pipeline.schema_version must be 1');
  for (const layer of layers) {
    const item = config[layer];
    if (!isObject(item)) throw new Error(`pipeline.${layer} must be an object`);
    if (Object.keys(item).some(k => !['provider', 'model', 'voice', 'profile', 'options'].includes(k))) throw new Error(`Unknown pipeline.${layer} field`);
    if (typeof item.provider !== 'string' || !/^[a-z][a-z0-9_]{0,39}$/.test(item.provider)) throw new Error(`pipeline.${layer}.provider is invalid`);
    if (typeof item.model !== 'string' || !/^[a-zA-Z0-9][a-zA-Z0-9._:/@+-]{0,255}$/.test(item.model)) throw new Error(`pipeline.${layer}.model is invalid`);
    for (const field of ['voice', 'profile'] as const) {
      const value = item[field];
      if (value !== undefined && (typeof value !== 'string' || !(field === 'profile' ? /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$/ : /^[a-zA-Z0-9][a-zA-Z0-9._:/@+-]{0,255}$/).test(value))) throw new Error(`pipeline.${layer}.${field} is invalid`);
      if (field === 'voice' && value !== undefined && layer !== 'tts') throw new Error('Only the TTS component accepts voice');
    }
    if (item.options !== undefined && !isObject(item.options)) throw new Error(`pipeline.${layer}.options must be an object`);
    const options = item.options ?? {};
    if (!isObject(options) || Object.keys(options).some(k => !['temperature', 'max_tokens', 'speed', 'stability', 'pitch', 'style', 'endpointing_ms', 'region', 'deployment', 'language', 'punctuate', 'interim_results'].includes(k))) throw new Error(`pipeline.${layer}.options contains unsupported or sensitive fields`);
    if (JSON.stringify(options).length > 2048 || Object.values(options).some(v => !['string', 'number', 'boolean'].includes(typeof v) || typeof v === 'number' && !Number.isFinite(v) || typeof v === 'string' && v.length > 256)) throw new Error('Component options must be bounded scalar values');
    rejectSecrets(item);
  }
  if (config.credentials !== undefined && (!isObject(config.credentials) || Object.keys(config.credentials).some(k => !['default', ...layers].includes(k)) || Object.values(config.credentials).some(v => !['auto', 'managed', 'byok'].includes(v)))) throw new Error('credentials must contain only default/stt/llm/tts modes: auto, managed or byok');
  for (const key of ['language', 'region', 'transport'] as const) {
    if (config[key] !== undefined && (typeof config[key] !== 'string' || config[key].length > 80 || !/^[a-zA-Z0-9_-]+$/.test(config[key]))) throw new Error(`pipeline.${key} must be a non-empty string`);
  }
  if (config.transport !== undefined && !['browser', 'phone', 'native', 'byo_twilio', 'byo_telnyx', 'byo_plivo', 'byo_sip'].includes(config.transport)) throw new Error('Unsupported pipeline transport');
  const result = copy({ ...config, schema_version: 1 as const, credentials: { default: 'auto' as const, ...config.credentials } });
  for (const layer of layers) if (result[layer].options && !Object.keys(result[layer].options!).length) delete result[layer].options;
  return result;
}
export function validateVoiceSelection(selection: VoiceSelection) {
  if (selection.pipeline != null) {
    if (selection.realtime != null) throw new Error('pipeline and realtime are mutually exclusive');
    normalizePipeline(selection.pipeline as PipelineConfig);
  }
}

export class SupafonePipeline extends SupafoneVoice {
  private readonly selection: PipelineConfig;
  constructor(client: SupafoneLabs, options: PipelineConfig) {
    super(client);
    this.selection = normalizePipeline(options);
  }
  get pipeline(): PipelineConfig { return copy(this.selection); }
  routePayload() { return { pipeline: this.pipeline, realtime: null }; }
  validate(context?: VoiceContext, agencyId?: string) { return this.client.labs.voice.validate(this.routePayload(), context, agencyId); }
}

/** Explicit runtime selection; automatic fallback is never implied. */
export class SupafoneRouter {
  constructor(private readonly client: SupafoneLabs) {}
  select(route: VoiceRoute): SupafoneVoice {
    if (!isObject(route)) throw new Error('route must be an object');
    if (route.kind === 'pipeline') {
      if (Object.keys(route).some(k => !['kind', 'pipeline'].includes(k))) throw new Error('A pipeline route accepts only kind and pipeline');
      return new SupafonePipeline(this.client, route.pipeline);
    }
    if (route.kind === 's2s' || route.kind === 'hybrid') {
      if (Object.keys(route).some(k => !['kind', 'provider', 'model', 'voice'].includes(k))) throw new Error('Unknown S2S route field');
      const provider = route.provider ?? (route.kind === 'hybrid' ? 'ultravox' : undefined);
      if (route.kind === 'hybrid' && provider !== 'ultravox') throw new Error('Ultravox is the first supported hybrid route');
      if (!provider) throw new Error('S2S provider is required');
      if (provider === 'ultravox' && !('model' in route) && !('voice' in route)) return new UltravoxS2S(this.client);
      return new SupafoneS2S(this.client, { provider, ...('model' in route ? { model: route.model } : {}), ...('voice' in route ? { voice: route.voice } : {}) });
    }
    throw new Error('route.kind must be hybrid, s2s or pipeline');
  }
  catalog(options: { layer?: VoiceLayer | 's2s' | 'hybrid' } = {}) { return this.client.labs.voice.catalog(options); }
  combinations(options: VoiceCombinationsOptions = {}) { return this.client.labs.voice.combinations(options); }
  validate(route: VoiceRoute, context?: VoiceContext, agencyId?: string) { return this.client.labs.voice.validate(this.select(route).routePayload(), context, agencyId); }
}

export class LabsVoiceNamespace {
  constructor(private readonly client: SupafoneLabs) {}
  catalog(options: { layer?: VoiceLayer | 's2s' | 'hybrid' } = {}): Promise<Record<string, unknown>> {
    if (options.layer && ![...layers, 's2s', 'hybrid'].includes(options.layer)) throw new Error('Invalid voice layer');
    return this.client.requestSupafoneApi('GET', '/api/v1/labs/voice/catalog' + (options.layer ? '?' + new URLSearchParams({ layer: options.layer }) : ''));
  }
  combinations(options: VoiceCombinationsOptions = {}): Promise<VoiceCombinationsResponse> {
    const offset = options.offset ?? 0, limit = options.limit ?? 100;
    if (!Number.isInteger(offset) || offset < 0 || !Number.isInteger(limit) || (limit < 1 || limit > 500)) throw new Error('offset must be non-negative and limit must be 1–500');
    if (options.filters && (Object.keys(options.filters).some(k => !layers.includes(k as VoiceLayer)) || Object.values(options.filters).some(values => !Array.isArray(values) || values.some(v => typeof v !== 'string' || !v)))) throw new Error('filters must map stt/llm/tts to endpoint ID lists');
    return this.client.requestSupafoneApi('POST', '/api/v1/labs/voice/combinations', { ...options, offset, limit });
  }
  validate(selection: VoiceSelection, context?: VoiceContext, agencyId?: string): Promise<Record<string, unknown>> {
    if (!isObject(selection) || !Object.keys(selection).length || Object.keys(selection).some(k => !['pipeline', 'realtime'].includes(k))) throw new Error('selection must contain pipeline or realtime');
    validateVoiceSelection(selection);
    return this.client.requestSupafoneApi('POST', '/api/v1/labs/voice/validate', { ...selection, ...(selection.pipeline != null ? { pipeline: normalizePipeline(selection.pipeline as PipelineConfig) } : {}), ...(context ? { context } : {}), ...(agencyId ? { agency_id: agencyId } : {}) });
  }
  private profilePath(provider: string, service: VoiceLayer, profile: string) {
    if (!layers.includes(service)) throw new Error('service must be stt, llm or tts');
    if ([provider, profile].some(v => typeof v !== 'string' || !v.trim())) throw new Error('provider and profile are required');
    return '/api/v1/labs/voice/profiles/' + [provider, service, profile].map(encodeURIComponent).join('/');
  }
  getProfile(provider: string, service: VoiceLayer, options: { profile?: string; agencyId?: string; mode?: VoiceCredentialMode } = {}): Promise<Record<string, unknown>> {
    if (options.mode && !['auto', 'managed', 'byok'].includes(options.mode)) throw new Error('Invalid credential mode');
    const query = new URLSearchParams({ ...(options.agencyId ? { agency_id: options.agencyId } : {}), ...(options.mode ? { mode: options.mode } : {}) }).toString();
    return this.client.requestSupafoneApi('GET', this.profilePath(provider, service, options.profile ?? 'default') + (query ? '?' + query : ''));
  }
  configureProfile(provider: string, service: VoiceLayer, options: { profile?: string; agencyId?: string; mode: 'managed' | 'byok'; credentials?: Record<string, unknown> }): Promise<Record<string, unknown>> {
    if (!['managed', 'byok'].includes(options.mode)) throw new Error('profile mode must be managed or byok');
    const credentials = options.credentials ?? {};
    if ((options.mode === 'managed' && Object.keys(credentials).length) || (options.mode === 'byok' && !Object.keys(credentials).length)) throw new Error('byok requires credentials; managed does not accept credentials');
    return this.client.requestSupafoneApi('PUT', this.profilePath(provider, service, options.profile ?? 'default'), { mode: options.mode, credentials, ...(options.agencyId ? { agency_id: options.agencyId } : {}) });
  }
}
