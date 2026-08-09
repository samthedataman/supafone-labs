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
