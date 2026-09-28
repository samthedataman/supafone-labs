import test from "node:test";
import assert from "node:assert/strict";
import { Supafone } from "../dist/index.js";

const providers = ["ultravox", "openai", "google", "xai", "smallest"];

for (const provider of providers) {
  test(`${provider}: readiness and account key modes reach the runtime API`, async (t) => {
    const calls = [];
    t.mock.method(globalThis, "fetch", async (url, init) => {
      calls.push({ url: String(url), method: init.method, payload: init.body ? JSON.parse(init.body) : undefined });
      return { ok: true, status: 200, text: async () => JSON.stringify({
        provider, configured: false, connected: true, source: "platform",
      }) };
    });
    const client = new Supafone({ apiKey: "sf_test_runtime" });
    const status = await client.labs.runtime.get({ provider, agencyId: "account/one" });
    const query = new URL(calls[0].url).searchParams;
    assert.equal(query.get("provider"), provider);
    assert.equal(query.get("agency_id"), "account/one");
    assert.equal(status.source, "platform");
    assert.equal(status.connected, true);
    await client.labs.runtime.configure({ provider, mode: "byok", credentials: { apiKey: "fixture-key" } });
    assert.deepEqual(calls.at(-1).payload, {
      provider, mode: "byok", credentials: { api_key: "fixture-key" },
    });
    await client.labs.runtime.configure({ provider, mode: "supafone_managed" });
    assert.deepEqual(calls.at(-1).payload, { provider, mode: "supafone_managed" });
  });
}

test("managed mode rejects conflicting credentials before making a request", (t) => {
  t.mock.method(globalThis, "fetch", () => { throw new Error("Unexpected request"); });
  const client = new Supafone({ apiKey: "sf_test_runtime" });
  for (const credentials of [{ apiKey: "fixture-key" }, { api_key: "fixture-key" }, { baseUrl: "https://example.test" }]) {
    assert.throws(() => client.labs.runtime.configure({ provider: "openai", mode: "supafone_managed", credentials }), /cannot include credentials/);
  }
  assert.throws(() => client.labs.runtime.configure({ mode: "unknown-mode" }), /runtime mode/);
});

test("omitting provider and mode retains the existing Ultravox request", async (t) => {
  let payload;
  t.mock.method(globalThis, "fetch", async (_url, init) => {
    payload = JSON.parse(init.body);
    return { ok: true, status: 200, text: async () => "{}" };
  });
  const client = new Supafone({ apiKey: "sf_test_runtime" });
  await client.labs.runtime.configure({ credentials: { apiKey: "fixture-key" } });
  assert.deepEqual(payload, { provider: "ultravox", credentials: { api_key: "fixture-key" } });
});
