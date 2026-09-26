import { test } from "node:test";
import assert from "node:assert/strict";
import Supafone, {
  SupafoneS2S, UltravoxS2S, OpenAIS2S, GeminiS2S, GrokS2S, HydraS2S,
} from "../dist/index.js";

function capture(t) {
  const calls = [];
  t.mock.method(globalThis, "fetch", async (url, init) => {
    calls.push({ url: String(url), method: init.method,
      payload: init.body ? JSON.parse(init.body) : undefined });
    return { ok: true, status: 200, text: async () => JSON.stringify({
      success: true, agent: { agent_key: "same-agent" },
    }) };
  });
  return { client: new Supafone({ apiKey: "sf_test" }), calls };
}

for (const [Adapter, provider] of [
  [UltravoxS2S, "ultravox"], [OpenAIS2S, "openai"], [GeminiS2S, "google"],
  [GrokS2S, "xai"], [HydraS2S, "smallest"],
]) {
  test(`${provider} uses the shared agent factory and preserves configuration`, async t => {
    const { client, calls } = capture(t);
    const engine = new Adapter(client);
    assert.ok(engine instanceof SupafoneS2S);
    const result = await engine.create({ name: "Concierge", goal: "Book a consultation", description: "Welcome callers and collect intake details",
      telephony: { mode: "byok", provider: "telnyx" } });
    assert.equal(result.agent.agent_key, "same-agent");
    assert.equal(calls[0].method, "POST");
    assert.match(calls[0].url, /\/api\/v1\/labs\/agents$/);
    assert.equal(calls[0].payload.telephony.provider, "telnyx");
    assert.equal(calls[0].payload.goal, "Book a consultation");
    assert.equal(calls[0].payload.description, "Welcome callers and collect intake details");
    assert.equal(engine.provider, provider);
    if (provider === "ultravox") assert.equal("realtime" in calls[0].payload, false);
    else {
      assert.deepEqual(calls[0].payload.realtime, { provider });
      assert.equal("call_stages" in calls[0].payload, false);
    }
  });
}

test("switch and reset only patch the same agent selection", async t => {
  const { client, calls } = capture(t);
  await new HydraS2S(client, { model: "hydra-v1.1", voice: "maya" }).apply("demo/one", { agencyId: "acct-1" });
  await new UltravoxS2S(client).apply("demo/one", { agencyId: "acct-1" });
  for (const call of calls) {
    assert.equal(call.method, "PATCH");
    assert.match(call.url, /\/api\/v1\/labs\/agents\/demo%2Fone\?agency_id=acct-1$/);
  }
  assert.deepEqual(calls[0].payload, { realtime: { provider: "smallest", model: "hydra-v1.1", voice: "maya" } });
  assert.deepEqual(calls[1].payload, { realtime: null });
});

test("preview does not implicitly apply a model switch", async t => {
  const { client, calls } = capture(t);
  await new HydraS2S(client).testCall("demo/one", { agencyId: "acct-1" });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].method, "POST");
  assert.match(calls[0].url, /\/api\/v1\/labs\/agents\/demo%2Fone\/test-call\?agency_id=acct-1$/);
});

test("optional Smallest account key aliases are preserved", async t => {
  const { client, calls } = capture(t);
  await new HydraS2S(client).create({ name: "Demo", providerKeys: { smallestApiKey: "test-key" } });
  assert.deepEqual(calls[0].payload.provider_keys, { smallest_api_key: "test-key" });
});

test("invalid or conflicting selections fail before network requests", t => {
  const { client, calls } = capture(t);
  assert.throws(() => new SupafoneS2S(client, { provider: "unknown" }), /Unsupported/);
  assert.throws(() => new SupafoneS2S(client, { model: "gpt-live-1" }), /voice settings/);
  assert.throws(() => new HydraS2S(client, { voice: " " }), /non-empty/);
  assert.throws(() => new HydraS2S(client).create({ name: "Conflict", realtime: {} }), /S2S adapter/);
  assert.throws(() => new HydraS2S(client).apply(""), /agentKey/);
  assert.equal(calls.length, 0);
});

test("exported selection is not mutable adapter state", t => {
  const { client } = capture(t);
  const engine = new HydraS2S(client, { model: "hydra-v1.0", voice: "sterling" });
  engine.realtime.provider = "xai";
  assert.equal(engine.realtime.provider, "smallest");
});
