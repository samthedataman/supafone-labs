import { test } from 'node:test';
import assert from 'node:assert/strict';
import Supafone, { SupafoneVoice, SupafoneS2S, UltravoxS2S, SupafonePipeline, SupafoneRouter, normalizePipeline, voiceCatalogSnapshot } from '../dist/index.js';

const config = {
  stt: { provider: 'cartesia', model: 'ink-2' },
  llm: { provider: 'openai', model: 'gpt-4.1' },
  tts: { provider: 'inworld', model: 'inworld-tts-2-flash', voice: 'Dennis' },
};
function record(t) {
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    calls.push({ url: String(url), method: init.method, body: init.body ? JSON.parse(init.body) : null });
    return { ok: true, status: 200, text: async () => JSON.stringify({ success: true }) };
  });
  return { client: new Supafone({ apiKey: 'sf_test' }), calls };
}

test('shared factory preserves Ultravox external voice; pipelines share Supervisor and Manager', async t => {
  const { client, calls } = record(t);
  const router = new SupafoneRouter(client);
  const hybrid = router.select({ kind: 'hybrid' });
  assert.ok(hybrid instanceof UltravoxS2S && hybrid instanceof SupafoneS2S && hybrid instanceof SupafoneVoice);
  await hybrid.create({ name: 'Desk', voice: { provider: 'cartesia', voiceId: 'existing-voice' } });
  assert.equal('pipeline' in calls.at(-1).body, false);
  assert.equal('realtime' in calls.at(-1).body, false);
  const pipeline = router.select({ kind: 'pipeline', pipeline: config });
  assert.ok(pipeline instanceof SupafoneVoice);
  await pipeline.create({ name: 'Desk', supervisor: true, manager: { enabled: true, reasoning: 'managed' } });
  assert.deepEqual(calls.at(-1).body.pipeline, normalizePipeline(config));
  assert.equal(calls.at(-1).body.voice_watcher, true);
  assert.equal(calls.at(-1).body.manager.enabled, true);
});

test('switching routes clears old route while preview only starts the saved agent', async t => {
  const { client, calls } = record(t);
  const pipeline = new SupafonePipeline(client, config);
  await pipeline.apply('desk/one', { agencyId: 'account 1' });
  assert.match(calls.at(-1).url, /agents\/desk%2Fone\?agency_id=account\+1$/);
  assert.deepEqual(calls.at(-1).body, { pipeline: normalizePipeline(config), realtime: null });
  await new UltravoxS2S(client).apply('desk');
  assert.deepEqual(calls.at(-1).body, { realtime: null });
  await client.labs.agents.update('desk', { pipeline: null });
  assert.deepEqual(calls.at(-1).body, { pipeline: null });
  await pipeline.testCall('desk');
  assert.equal(calls.at(-1).body, null);
  assert.match(calls.at(-1).url, /agents\/desk\/test-call$/);
});

test('all eight mixed credential vectors preserve modes independently', async t => {
  const { client, calls } = record(t);
  for (const stt of ['managed', 'byok']) for (const llm of ['managed', 'byok']) for (const tts of ['managed', 'byok']) {
    await new SupafonePipeline(client, { ...config, credentials: { stt, llm, tts } }).apply('desk');
    assert.deepEqual(calls.at(-1).body.pipeline.credentials, { default: 'auto', stt, llm, tts });
  }
});

test('ambiguous, malformed and secret-bearing configuration never requests a vendor', t => {
  const { client, calls } = record(t);
  const changes = [
    { schema_version: 2 }, { schema_version: true }, { stt: null },
    { llm: { provider: 'openai', model: ' ' } },
    { tts: { ...config.tts, api_key: 'secret' } },
    { stt: { ...config.stt, options: { authorization: 'secret' } } },
    { stt: { ...config.stt, voice: 'bad' } },
    { llm: { ...config.llm, options: { temperature: NaN } } },
    { credentials: { default: 'fallback' } }, { transport: 'unknown' },
  ];
  for (const change of changes) assert.throws(() => new SupafonePipeline(client, { ...config, ...change }));
  assert.throws(() => client.labs.agents.create({ name: 'Desk', pipeline: config, realtime: { provider: 'openai' } }), /mutually exclusive/);
  assert.throws(() => new SupafoneS2S(client).create({ name: 'Desk', pipeline: config }), /adapter/);
  assert.equal(calls.length, 0);
});

test('profile and catalog requests have their own service-scoped contract', async t => {
  const { client, calls } = record(t);
  await client.labs.voice.catalog({ layer: 'stt' });
  assert.match(calls.at(-1).url, /voice\/catalog\?layer=stt$/);
  await client.labs.voice.combinations({ context: { language: 'en' }, filters: { stt: ['stt/cartesia/ink-2'] }, offset: 100, limit: 50 });
  assert.deepEqual(calls.at(-1).body, { context: { language: 'en' }, filters: { stt: ['stt/cartesia/ink-2'] }, offset: 100, limit: 50 });
  await new SupafonePipeline(client, config).validate({ transport: 'browser' });
  assert.deepEqual(calls.at(-1).body, { pipeline: normalizePipeline(config), realtime: null, context: { transport: 'browser' } });
  await client.labs.voice.configureProfile('google', 'stt', { profile: 'work', mode: 'byok', credentials: { project_id: 'project', service_account_json: JSON.stringify({ type: 'service_account', private_key: 'test-secret', project_id: 'project', client_email: 'service@test.example', token_uri: 'https://oauth2.googleapis.com/token' }) } });
  assert.match(calls.at(-1).url, /voice\/profiles\/google\/stt\/work$/);
  await client.labs.voice.getProfile('google', 'stt', { profile: 'work' });
  assert.equal(calls.at(-1).method, 'GET');
  await client.labs.voice.configureProfile('google', 'stt', { mode: 'managed' });
  assert.deepEqual(calls.at(-1).body, { mode: 'managed', credentials: {} });
  const before = calls.length;
  assert.throws(() => client.labs.voice.configureProfile('google', 'stt', { mode: 'managed', credentials: { api_key: 'no' } }));
  assert.equal(calls.length, before);
});

test('every catalog triple uses the same selection contract without a curated bundle allowlist', t => {
  const { client } = record(t);
  const catalog = voiceCatalogSnapshot();
  const layers = ['stt', 'llm', 'tts'].map(layer => catalog.components.filter(entry => entry.layer === layer));
  let count = 0;
  for (const stt of layers[0]) for (const llm of layers[1]) for (const tts of layers[2]) {
    const route = Object.fromEntries(['stt', 'llm', 'tts'].map((layer, i) => [layer, { provider: [stt,llm,tts][i].provider, model: [stt,llm,tts][i].model }]));
    const engine = new SupafoneRouter(client).select({ kind: 'pipeline', pipeline: route });
    for (const layer of ['stt', 'llm', 'tts']) assert.deepEqual(engine.routePayload().pipeline[layer], route[layer]);
    count++;
  }
  assert.equal(count, layers[0].length * layers[1].length * layers[2].length);
});

test('configuration and snapshot access never expose mutable adapter state', t => {
  const { client } = record(t);
  const source = structuredClone(config);
  const engine = new SupafonePipeline(client, source);
  source.stt.model = 'changed';
  engine.pipeline.tts.voice = 'changed';
  assert.equal(engine.pipeline.stt.model, 'ink-2');
  assert.equal(engine.pipeline.tts.voice, 'Dennis');
  const snapshot = voiceCatalogSnapshot();
  snapshot.components[0].model = 'changed';
  assert.notEqual(voiceCatalogSnapshot().components[0].model, 'changed');
});


test('pipeline and router convenience preflight preserve the selected workspace', async t => {
  const { client, calls } = record(t);
  await new SupafonePipeline(client, config).validate({ language: 'en' }, 'other-account');
  assert.equal(calls.at(-1).body.agency_id, 'other-account');
  await new SupafoneRouter(client).validate({ kind: 'hybrid' }, undefined, 'other-account');
  assert.deepEqual(calls.at(-1).body, { realtime: null, agency_id: 'other-account' });
});
