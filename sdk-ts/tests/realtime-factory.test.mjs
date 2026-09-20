import { test } from "node:test";
import assert from "node:assert/strict";

import Supafone from "../dist/index.js";

function mockFetch(log, responses = []) {
  return async (url, init) => {
    log.push({
      url: String(url),
      method: init?.method,
      body: init?.body ? JSON.parse(init.body) : undefined,
    });
    const body = responses.shift() ?? { success: true, agent: { agent_key: "demo" }, runtime: {} };
    return { ok: true, status: 200, text: async () => JSON.stringify(body) };
  };
}

test("realtime factory payload preserves model and omits generated stages", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch(log));
  const client = new Supafone({ apiKey: "sf_test" });

  await client.labs.agents.createOutbound({
    name: "Phone demo",
    realtime: {
      provider: "xai",
      model: "grok-voice-latest",
      voice: "eve",
    },
    telephony: { mode: "byok", provider: "telnyx" },
  });

  assert.deepEqual(log[0].body.realtime, {
    provider: "xai",
    model: "grok-voice-latest",
    voice: "eve",
  });
  assert.equal("call_stages" in log[0].body, false);
});

test("testCall uses the authenticated agent route", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch(log, [{ simulated: true }]));
  const client = new Supafone({ apiKey: "sf_test" });

  const result = await client.labs.agents.testCall("demo/one", { agencyId: "acct-1" });

  assert.deepEqual(result, { simulated: true });
  assert.equal(log[0].method, "POST");
  assert.match(log[0].url, /\/api\/v1\/labs\/agents\/demo%2Fone\/test-call\?agency_id=acct-1$/);
});
