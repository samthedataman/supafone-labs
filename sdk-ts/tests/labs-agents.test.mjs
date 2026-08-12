// labs.agents voice_watcher client flag — run via `npm test` (builds first,
// then node --test against the ESM dist). Mocks global fetch; no framework deps.
import { test } from "node:test";
import assert from "node:assert/strict";

import Supafone from "../dist/index.js";

function mockFetch(responses, log) {
  return async (url, init) => {
    log.push({
      url: String(url),
      method: init?.method,
      body: init?.body ? JSON.parse(init.body) : undefined,
    });
    const { status = 200, body = {} } = responses.shift() ?? {};
    return { ok: status < 400, status, text: async () => JSON.stringify(body) };
  };
}

const agentResponse = { body: { success: true, agent: { agent_key: "vw" }, runtime: {} } };

test("voiceWatcher defaults on and injects into the create payload", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([agentResponse], log));
  const sf = new Supafone({ apiKey: "sf_test" });
  assert.equal(sf.voiceWatcher, true);
  await sf.labs.agents.createInbound({ agentKey: "vw", name: "VW default" });
  assert.equal(log[0].body.voice_watcher, true);
});

test("voiceWatcher:false is stored and injected into the payload", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([agentResponse], log));
  const sf = new Supafone({ apiKey: "sf_test", voiceWatcher: false });
  assert.equal(sf.voiceWatcher, false);
  await sf.labs.agents.createOutbound({ agentKey: "vw", name: "VW off" });
  assert.equal(log[0].body.voice_watcher, false);
});

test("an explicit caller voice_watcher value is preserved", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([agentResponse], log));
  // Client default is on, but the caller disables it on this agent.
  const sf = new Supafone({ apiKey: "sf_test", voiceWatcher: true });
  await sf.labs.agents.create({ agentKey: "vw", name: "VW explicit", voiceWatcher: false });
  assert.equal(log[0].body.voice_watcher, false);
});

test("deprecated labs alias sets voiceWatcher", () => {
  const sf = new Supafone({ apiKey: "sf_test", labs: false });
  assert.equal(sf.voiceWatcher, false);
});

test("languageVoiceRouting serializes the public opt-in contract", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([agentResponse], log));
  const sf = new Supafone({ apiKey: "sf_test" });

  await sf.labs.agents.createInbound({
    agentKey: "bilingual",
    name: "Bilingual intake",
    languageVoiceRouting: true,
    routingLanguages: ["en-US", "es-MX"],
  });

  assert.equal(log[0].body.language_voice_routing, true);
  assert.deepEqual(log[0].body.routing_languages, ["en-US", "es-MX"]);
  assert.equal("language_profiles" in log[0].body, false);
});

test("languageVoiceRouting is absent unless the developer opts in", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([agentResponse], log));
  const sf = new Supafone({ apiKey: "sf_test" });

  await sf.labs.agents.createInbound({ agentKey: "legacy", name: "Legacy" });

  assert.equal("language_voice_routing" in log[0].body, false);
  assert.equal("routing_languages" in log[0].body, false);
});

test("languageProfiles serialize only documented public fields", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([agentResponse], log));
  const sf = new Supafone({ apiKey: "sf_test" });

  await sf.labs.agents.createInbound({
    agentKey: "curated",
    name: "Curated bilingual agent",
    languageVoiceRouting: true,
    languageProfiles: [
      {
        language: "en-US",
        languageHint: "en-US",
        privatePolicy: "must-not-serialize",
        voice: {
          provider: "cartesia",
          voiceId: "voice-en",
          model: "sonic-3.5",
          apiKey: "must-not-serialize",
        },
      },
      { language: "es-MX", voice: { provider: "cartesia", voiceId: "voice-es" } },
    ],
  });

  assert.deepEqual(log[0].body.language_profiles[0], {
    language: "en-US",
    language_hint: "en-US",
    voice: { provider: "cartesia", voice_id: "voice-en", model: "sonic-3.5" },
  });
  assert.equal("privatePolicy" in log[0].body.language_profiles[0], false);
});

test("languageProfiles are not silently truncated before backend validation", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([agentResponse], log));
  const sf = new Supafone({ apiKey: "sf_test" });

  await sf.labs.agents.createInbound({
    agentKey: "too-many-profiles",
    name: "Too many profiles",
    languageVoiceRouting: true,
    languageProfiles: ["en-US", "es-MX", "fr-FR", "de-DE", "vi-VN"].map((language) => ({
      language,
    })),
  });

  assert.equal(log[0].body.language_profiles.length, 5);
});
