import { test } from "node:test";
import assert from "node:assert/strict";

import Supafone from "../dist/index.js";

function jsonResponse(payload) {
  return {
    ok: true,
    status: 200,
    text: async () => JSON.stringify(payload),
  };
}

test("voice catalog exposes live paging, capabilities, matching, preview, and agent selection", async (t) => {
  const calls = [];
  t.mock.method(globalThis, "fetch", async (url, init = {}) => {
    const parsed = new URL(String(url));
    const body = init.body ? JSON.parse(init.body) : undefined;
    calls.push({ path: parsed.pathname, search: parsed.search, body });

    if (parsed.pathname.endsWith("/voices/capabilities")) {
      return jsonResponse({
        runtime: "ultravox",
        runtime_spoken_language_count: 26,
        runtime_spoken_languages: [],
        providers: [{ provider: "cartesia_sonic", models: [] }],
        selection_rule: {},
        normalization_schema_version: 1,
      });
    }
    if (parsed.pathname.endsWith("/voices/recommend")) {
      return jsonResponse({ description: body.description, matches: [], total_considered: 2 });
    }
    if (parsed.pathname.endsWith("/voices/preview")) {
      const bytes = Uint8Array.from([1, 2, 3]).buffer;
      return {
        ok: true,
        status: 200,
        headers: { get: () => "audio/mpeg" },
        arrayBuffer: async () => bytes,
        text: async () => "",
      };
    }
    if (parsed.pathname.endsWith("/voices")) {
      const cursor = Number(parsed.searchParams.get("cursor") || 0);
      return jsonResponse({
        voices: [{ id: `cartesia-sonic:voice-${cursor}`, provider_key: "cartesia_sonic", model: "sonic-3.5" }],
        total: 2,
        cursor,
        next_cursor: cursor === 0 ? 1 : null,
        providers: [],
      });
    }
    if (parsed.pathname.endsWith("/agents")) {
      return jsonResponse({ agent: { id: "agent-1" } });
    }
    throw new Error(`Unexpected path ${parsed.pathname}`);
  });

  const sf = new Supafone({ apiKey: "sl_test" });
  const catalog = await sf.labs.voices.listAll({
    provider: "cartesia_sonic",
    language: "es-MX",
    compatibleLanguage: "es",
    gender: "female",
    voiceType: "warm empathetic",
    model: "sonic-3.5",
    runtimeProvider: "cartesia",
    configuredOnly: true,
    search: "warm",
    pageSize: 1,
  });
  assert.equal(catalog.voices.length, 2);
  assert.match(calls[0].search, /provider=cartesia_sonic/);
  assert.match(calls[0].search, /language=es-MX/);
  assert.match(calls[0].search, /compatible_language=es/);
  assert.match(calls[0].search, /gender=female/);
  assert.match(calls[0].search, /voice_type=warm(%20|\+)empathetic/);
  assert.match(calls[0].search, /model=sonic-3.5/);
  assert.match(calls[0].search, /runtime_provider=cartesia/);
  assert.match(calls[0].search, /configured_only=true/);
  assert.match(calls[0].search, /search=warm/);

  const capabilities = await sf.labs.voices.capabilities();
  assert.equal(capabilities.runtime_spoken_language_count, 26);

  await sf.labs.voices.recommend({
    description: "warm Latin American support voice",
    language: "es",
    provider: "cartesia",
    voiceType: "warm_empathetic",
    model: "sonic-3.5",
    configuredOnly: true,
    limit: 3,
  });
  const recommendation = calls.find((call) => call.path.endsWith("/voices/recommend"));
  assert.deepEqual(recommendation.body, {
    description: "warm Latin American support voice",
    language: "es",
    provider: "cartesia",
    voice_type: "warm_empathetic",
    model: "sonic-3.5",
    configured_only: true,
    limit: 3,
  });

  const selection = sf.labs.voices.selection({
    id: "cartesia-sonic:voice-1",
    provider_key: "cartesia_sonic",
    model: "sonic-3.5",
  });
  assert.deepEqual(selection, {
    provider: "cartesia_sonic",
    voiceId: "cartesia-sonic:voice-1",
    model: "sonic-3.5",
  });

  const preview = await sf.labs.voices.preview("cartesia-sonic:voice-1");
  assert.equal(preview.mediaType, "audio/mpeg");
  assert.equal(preview.content.byteLength, 3);

  await sf.labs.agents.create({
    name: "Spanish intake",
    preferredLanguage: "es-MX",
    voicePreference: {
      description: "female Spanish patient support voice",
      configuredOnly: true,
    },
  });
  const agentCreate = calls.find((call) => call.path.endsWith("/agents"));
  assert.deepEqual(agentCreate.body.voice_preference, {
    description: "female Spanish patient support voice",
    language: "es-MX",
    configured_only: true,
  });
  assert.equal(agentCreate.body.language, "es-MX");
});
