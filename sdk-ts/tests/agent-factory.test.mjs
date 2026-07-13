import { test } from "node:test";
import assert from "node:assert/strict";

import Supafone from "../dist/index.js";

function mockFetch(log) {
  return async (url, init) => {
    log.push({
      url: String(url),
      body: init?.body ? JSON.parse(init.body) : undefined,
    });
    return {
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ agent: { id: "agent-1" } }),
    };
  };
}

test("agent factory preserves the published Voice Watcher default", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch(log));

  const sf = new Supafone({ apiKey: "sl_test" });
  await sf.labs.agents.create({ name: "Receptionist" });

  assert.equal(sf.voiceWatcher, true);
  assert.equal(log[0].body.voice_watcher, true);
});

test("agent factory honors an explicit watcher override", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch(log));

  const sf = new Supafone({ apiKey: "sl_test", voiceWatcher: false });
  await sf.labs.agents.create({ name: "Raw agent" });

  assert.equal(log[0].body.voice_watcher, false);
});

test("agent factory preserves native Ultravox BYOK configuration", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch(log));

  const sf = new Supafone({ apiKey: "sl_test" });
  await sf.labs.agents.create({
    name: "BYOK agent",
    byok: {
      ultravox: { api_key: "uv_test", base_url: "https://api.ultravox.ai" },
      tts: { provider: "cartesia", api_key: "cartesia_test" },
    },
  });

  assert.deepEqual(log[0].body.byok.ultravox, {
    api_key: "uv_test",
    base_url: "https://api.ultravox.ai",
  });
});
