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
