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
  assert.equal("call_stages" in log[0].body, false);
});

test("hosted planner uses the product API and never sends provider secrets", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", async (url, init) => {
    log.push({ url: String(url), body: JSON.parse(init.body) });
    return {
      ok: true,
      status: 200,
      text: async () => JSON.stringify({
        version: "supafone_call_plan_v1",
        summary: "Ready",
        base_system_prompt: "Be accurate",
        call_stages: [],
        generated_by: "supafone_hosted_haiku",
        model: "haiku",
        fallback: false,
      }),
    };
  });

  const sf = new Supafone({ apiKey: "sl_test_one_key" });
  const plan = await sf.generateCallStages({
    name: "Demo setter",
    description: "Qualify warm leads and book a demo",
    direction: "outbound",
    stageCount: 5,
    telephony: { mode: "byok", credentials: { authToken: "never-send-this" } },
  });

  assert.equal(plan.generated_by, "supafone_hosted_haiku");
  assert.equal(log[0].url, "https://api.supafone.ai/api/v1/labs/agent-plans");
  assert.equal(log[0].body.description, "Qualify warm leads and book a demo");
  assert.equal("telephony" in log[0].body, false);
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

test("hosted discovery, voice filters, and runtime have REST parity", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", async (url, init) => {
    log.push({
      url: String(url),
      method: init?.method,
      body: init?.body ? JSON.parse(init.body) : undefined,
    });
    return {
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ ok: true }),
    };
  });

  const sf = new Supafone({ apiKey: "sl_test" });
  await sf.labs.presets.list();
  await sf.labs.tools.list();
  await sf.labs.voices.list({
    provider: "cartesia", search: "warm", language: "en-US", cursor: 10, limit: 25,
  });
  await sf.labs.runtime.get({ agencyId: "acct_123" });
  await sf.labs.runtime.configure({
    provider: "ultravox",
    credentials: { apiKey: "uvx_test", baseUrl: "https://api.ultravox.ai/api" },
  });

  assert.equal(log[0].url, "https://api.supafone.ai/api/v1/labs/presets");
  assert.equal(log[1].url, "https://api.supafone.ai/api/v1/labs/tools");
  assert.equal(
    log[2].url,
    "https://api.supafone.ai/api/v1/labs/voices?provider=cartesia&search=warm&language=en-US&cursor=10&limit=25",
  );
  assert.equal(log[3].url, "https://api.supafone.ai/api/v1/labs/runtime?agency_id=acct_123");
  assert.deepEqual(log[4].body, {
    provider: "ultravox",
    credentials: { api_key: "uvx_test", base_url: "https://api.ultravox.ai/api" },
  });
});

test("billing returns a hosted checkout link and supports status polling", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", async (url, init) => {
    log.push({ url: String(url), method: init?.method, body: init?.body ? JSON.parse(init.body) : undefined });
    const status = String(url).endsWith("/cs_test_123");
    return {
      ok: true,
      status: 200,
      text: async () => JSON.stringify(status
        ? { status: "paid", checkout_session_id: "cs_test_123", ready_to_provision: true }
        : {
            status: "requires_payment",
            checkout_session_id: "cs_test_123",
            checkout_url: "https://checkout.stripe.com/c/pay/test",
            kind: "number_addon",
          }),
    };
  });

  const sf = new Supafone({ apiKey: "sl_test" });
  const checkout = await sf.labs.billing.checkout({
    kind: "number_addon",
    numberStrategy: "dedicated",
    phoneNumber: "+14155550123",
  });
  const status = await sf.labs.billing.status(checkout.checkout_session_id);

  assert.equal(checkout.status, "requires_payment");
  assert.equal(status.ready_to_provision, true);
  assert.deepEqual(log[0].body, {
    kind: "number_addon",
    number_strategy: "dedicated",
    phone_number: "+14155550123",
  });
  assert.match(log[0].url, /api\.labs\.supafone\.ai\/v1\/billing\/checkout$/);
});

test("paid number buy opens checkout before provisioning and reuses the paid session", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", async (url, init) => {
    const entry = {
      url: String(url),
      method: init?.method,
      body: init?.body ? JSON.parse(init.body) : undefined,
    };
    log.push(entry);
    const checkout = entry.url.endsWith("/v1/billing/checkout");
    return {
      ok: true,
      status: 200,
      text: async () => JSON.stringify(checkout
        ? {
            status: "requires_payment",
            checkout_session_id: "cs_test_number",
            checkout_url: "https://checkout.stripe.com/c/pay/test-number",
            kind: "number_addon",
          }
        : { success: true, number: { number_id: "num_123" } }),
    };
  });

  const sf = new Supafone({ apiKey: "sl_test" });
  const checkout = await sf.labs.phoneNumbers.buy({
    phoneNumber: "+14155550123",
    numberStrategy: "premium",
  });
  const provisioned = await sf.labs.phoneNumbers.buy({
    phoneNumber: "+14155550123",
    numberStrategy: "premium",
    billingCheckoutSessionId: checkout.checkout_session_id,
  });

  assert.equal(checkout.status, "requires_payment");
  assert.equal(provisioned.number.number_id, "num_123");
  assert.match(log[0].url, /api\.labs\.supafone\.ai\/v1\/billing\/checkout$/);
  assert.deepEqual(log[0].body, {
    kind: "number_addon",
    number_strategy: "premium",
    phone_number: "+14155550123",
  });
  assert.match(log[1].url, /api\.supafone\.ai\/api\/v1\/labs\/phone-numbers$/);
  assert.equal(log[1].body.billing_checkout_session_id, "cs_test_number");
});
