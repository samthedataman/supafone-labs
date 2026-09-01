import { test } from "node:test";
import assert from "node:assert/strict";

import Supafone, { SupafoneLabsError } from "../dist/index.js";

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

test("structured payment errors stay readable and machine actionable", async (t) => {
  t.mock.method(globalThis, "fetch", async () => ({
    ok: false,
    status: 402,
    text: async () => JSON.stringify({
      detail: {
        code: "managed_minutes_exhausted",
        message: "Your five free managed minutes have been used.",
        checkout_endpoint: "/v1/billing/checkout",
      },
    }),
  }));

  const sf = new Supafone({ apiKey: "sl_test" });
  await assert.rejects(
    () => sf.labs.billing.topUp(),
    (error) => {
      assert.ok(error instanceof SupafoneLabsError);
      assert.equal(error.status, 402);
      assert.match(error.message, /Your five free managed minutes have been used\./);
      assert.equal(error.body.detail.checkout_endpoint, "/v1/billing/checkout");
      return true;
    },
  );
});

test("agent factory preserves the published Supervisor default", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch(log));

  const sf = new Supafone({ apiKey: "sl_test" });
  await sf.labs.agents.create({ name: "Receptionist" });

  assert.equal(sf.supervisor, true);
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

test("agent factory honors an explicit Supervisor override", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch(log));

  const sf = new Supafone({ apiKey: "sl_test", supervisor: false });
  await sf.labs.agents.create({ name: "Raw agent" });

  assert.equal(log[0].body.voice_watcher, false);
});

test("agent factory serializes every BYOK Supervisor provider", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch(log));

  const sf = new Supafone({ apiKey: "sl_test" });
  for (const provider of ["anthropic", "openai", "gemini", "openrouter", "groq", "cerebras"]) {
    await sf.labs.agents.create({
      name: `${provider} supervised agent`,
      supervisor: {
        mode: "byok",
        provider,
        model: "selected-model",
        apiKey: `${provider}-secret`,
      },
    });
  }

  assert.equal(log.length, 6);
  for (const [index, provider] of ["anthropic", "openai", "gemini", "openrouter", "groq", "cerebras"].entries()) {
    assert.deepEqual(log[index].body.supervisor, {
      mode: "byok",
      provider,
      model: "selected-model",
      api_key: `${provider}-secret`,
    });
    assert.equal(log[index].body.voice_watcher, true);
  }
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

test("agent factory serializes executable custom tools and per-agent SMTP", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch(log));

  const sf = new Supafone({ apiKey: "sl_test" });
  await sf.labs.agents.createInbound({
    name: "Support intake",
    tools: {
      email: true,
      ivrNavigation: true,
      customTools: [{
        name: "lookup_order",
        description: "Read a confirmed order status.",
        url: "https://api.acme.example/orders",
        header: "X-API-Key",
        apiKey: "tool-secret",
        params: [
          { name: "order_id", type: "string", required: true },
          { name: "include_history", type: "boolean" },
        ],
        stages: ["support", "confirmation"],
      }],
    },
    email: {
      enabled: true,
      fromEmail: "support@acme.example",
      smtpHost: "smtp.acme.example",
      smtpPort: 587,
      smtpUser: "support@acme.example",
      smtpPassword: "smtp-secret",
    },
  });

  assert.equal(log[0].body.tools.ivr_navigation, true);
  assert.equal(log[0].body.tools.custom_tools[0].params[1].type, "boolean");
  assert.deepEqual(log[0].body.tools.custom_tools[0].stages, ["support", "confirmation"]);
  assert.equal(log[0].body.email.smtp_host, "smtp.acme.example");
  assert.equal(log[0].body.email.smtp_pass, "smtp-secret");
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

test("agent updates and website corpus methods preserve the native API contract", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", async (url, init) => {
    log.push({
      url: String(url),
      method: init?.method,
      body: typeof init?.body === "string" ? JSON.parse(init.body) : undefined,
    });
    return {
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ agent: { id: "agent-1" } }),
    };
  });

  const sf = new Supafone({ apiKey: "sl_test" });
  await sf.labs.agents.update("agent-key", {
    websiteUrl: "",
    systemPrompt: "Use only verified facts.",
    tools: { callRouting: true },
    recording: { recordAudio: true, retentionDays: 14 },
  });
  await sf.labs.agents.syncKnowledge("agent-1", { websiteUrl: "https://example.com" });
  await sf.labs.agents.detachWebsiteKnowledge("agent-1");

  assert.deepEqual(log[0].body, {
    website_url: "",
    system_prompt: "Use only verified facts.",
    recording: { record_audio: true, retention_days: 14 },
    tools: { call_routing: true },
  });
  assert.equal(log[0].method, "PATCH");
  assert.match(log[0].url, /\/api\/v1\/labs\/agents\/agent-key$/);
  assert.deepEqual(log[1].body, { url: "https://example.com" });
  assert.match(log[1].url, /\/api\/v1\/agents\/agent-1\/sync-knowledge$/);
  assert.equal(log[2].method, "DELETE");
  assert.match(log[2].url, /\/api\/v1\/agents\/agent-1\/knowledge\/website$/);
});

test("agent-scoped WebRTC and knowledge methods expose all durable artifacts", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", async (url, init) => {
    const body = init?.body;
    log.push({
      url: String(url),
      method: init?.method,
      body: typeof body === "string" ? JSON.parse(body) : body,
    });
    return {
      ok: true,
      status: 200,
      text: async () => JSON.stringify({
        success: true,
        agent: { id: "agent-1" },
        browser_session: { provider: "ultravox", transport: "webrtc", join_url: "https://join" },
      }),
    };
  });

  const sf = new Supafone({ apiKey: "sl_test" });
  await sf.labs.agents.startWebRtcCall("agent-1");
  await sf.labs.agents.reindexKnowledge("agent-1");
  await sf.labs.agents.uploadKnowledgeDocument(
    "agent-1",
    new TextEncoder().encode("Verified policy"),
    'policy"\r\nX-Injected.txt',
  );
  await sf.labs.agents.deleteKnowledgeDocument("agent-1", "doc/unsafe");
  await sf.labs.agents.chatKnowledge(
    "agent-1",
    "What is the policy?",
    [{ role: "user", content: "Use saved sources." }],
  );

  assert.match(log[0].url, /\/api\/v1\/agents\/agent-1\/test-call$/);
  assert.match(log[1].url, /\/api\/v1\/agents\/agent-1\/knowledge\/reindex$/);
  assert.ok(log[2].body instanceof FormData);
  assert.equal(log[2].body.get("file").name, "policyX-Injected.txt");
  assert.match(log[3].url, /\/knowledge\/docs\/doc%2Funsafe$/);
  assert.deepEqual(log[4].body, {
    message: "What is the policy?",
    history: [{ role: "user", content: "Use saved sources." }],
  });
});

test("agent factory rejects a fifth language profile before sending a request", (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch(log));

  const sf = new Supafone({ apiKey: "sl_test" });
  assert.throws(
    () => sf.labs.agents.create({
      name: "Too many profiles",
      languageProfiles: ["en-US", "es-MX", "fr-FR", "de-DE", "vi-VN"].map(
        (language) => ({ language }),
      ),
    }),
    /at most four/,
  );
  assert.equal(log.length, 0);
});

test("shared phone pool exposes a safe snapshot and scoped realtime socket", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", async (url, init) => {
    log.push({ url: String(url), method: init?.method });
    return {
      ok: true,
      status: 200,
      text: async () => JSON.stringify({
        version: "developer_phone_pool_v1",
        revision: "rev-1",
        counts: { total: 1, available: 1, in_use: 0, unavailable: 0 },
        numbers: [{ phone_number: "+14155550123", status: "available", available: true }],
        stream: {
          url: "/api/v1/labs/phone-numbers/pool/stream",
          token: "pool-only-token",
          protocol: "developer_phone_pool_v1",
          expires_in_seconds: 600,
        },
      }),
    };
  });

  class FakeWebSocket {
    static last;
    constructor(url, protocol) {
      this.url = url;
      this.protocol = protocol;
      FakeWebSocket.last = this;
    }
    addEventListener(name, callback) {
      if (name === "open") queueMicrotask(callback);
    }
  }

  const sf = new Supafone({ apiKey: "sl_test" });
  const snapshot = await sf.labs.phoneNumbers.pool();
  assert.equal(snapshot.counts.available, 1);
  const socket = await sf.labs.phoneNumbers.connectPool({ WebSocketImpl: FakeWebSocket });
  assert.equal(socket.protocol, "developer_phone_pool_v1");
  assert.match(socket.url, /^wss:\/\/api\.supafone\.ai\/api\/v1\/labs\/phone-numbers\/pool\/stream/);
  assert.match(socket.url, /token=pool-only-token/);
  assert.equal(socket.url.includes("sl_test"), false);
  assert.equal(log.length, 2);
});

test("create with a shared number selects only available enrolled pool inventory", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", async (url, init) => {
    const path = new URL(String(url)).pathname;
    const body = init?.body ? JSON.parse(init.body) : undefined;
    log.push({ path, method: init?.method, body });
    if (path === "/api/v1/labs/agents") {
      return {
        ok: true,
        status: 200,
        text: async () => JSON.stringify({ agent: { agent_key: "shared-agent" } }),
      };
    }
    if (path === "/api/v1/labs/phone-numbers/pool") {
      return {
        ok: true,
        status: 200,
        text: async () => JSON.stringify({
          numbers: [
            { phone_number: "+12125550199", available: false, status: "in_use" },
            { phone_number: "+14155550123", available: true, status: "available" },
          ],
        }),
      };
    }
    if (path === "/api/v1/labs/phone-numbers") {
      return {
        ok: true,
        status: 200,
        text: async () => JSON.stringify({ number: { phone_number: body.phone_number } }),
      };
    }
    throw new Error(`Unexpected request: ${path}`);
  });

  const sf = new Supafone({ apiKey: "sl_test" });
  const result = await sf.labs.agents.createInboundWithNumber({
    agentKey: "shared-agent",
    name: "Shared agent",
    number: {
      numberStrategy: "default_pool",
      search: { areaCode: "415" },
    },
  });

  assert.equal(result.number.number.phone_number, "+14155550123");
  assert.deepEqual(log.map((item) => item.path), [
    "/api/v1/labs/agents",
    "/api/v1/labs/phone-numbers/pool",
    "/api/v1/labs/phone-numbers",
  ]);
  assert.equal(log[2].body.number_strategy, "default_pool");
  assert.equal(log[2].body.phone_number, "+14155550123");
});
