// Campaigns namespace + account auth — run via `npm test` (builds first, then
// node --test against the ESM dist). Mocks global fetch; no framework deps.
import { test } from "node:test";
import assert from "node:assert/strict";

import Supafone, { SupafoneLabsError } from "../dist/index.js";

function mockFetch(responses, log) {
  return async (url, init) => {
    log.push({
      url: String(url),
      method: init?.method,
      auth: init?.headers?.Authorization ?? null,
      body: init?.body ? JSON.parse(init.body) : undefined,
    });
    const { status = 200, body = {} } = responses.shift() ?? {};
    return {
      ok: status < 400,
      status,
      text: async () => JSON.stringify(body),
    };
  };
}

test("constructor accepts account auth without an apiKey", () => {
  const sf = new Supafone({ accountToken: "jwt-test" });
  assert.ok(sf.campaigns);
  assert.throws(() => new Supafone({}), SupafoneLabsError);
});

test("campaign flow emits the product-API routes with the account token", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([
    { body: { campaign: { id: "c1", name: "Chase", goal: "book", status: "draft" } } },
    { body: { campaign: { id: "c1", status: "draft" } } },
    { body: { added: 1, stats: {} } },
    { body: { campaign: { id: "c1", status: "active" } } },
  ], log));

  const sf = new Supafone({ accountToken: "jwt-abc" });
  const { campaign } = await sf.campaigns.create({ name: "Chase", goal: "book", agentId: "agent-1" });
  await sf.campaigns.applyPreset(campaign.id, "win_back");
  await sf.campaigns.addRecipients(campaign.id, [{ name: "Jane", phone: "+15551234567", outreach_consent: "yes" }]);
  await sf.campaigns.launch(campaign.id);

  assert.deepEqual(log.map((r) => r.url.split("api.supafone.ai")[1]), [
    "/api/v1/campaigns",
    "/api/v1/campaigns/c1/apply-preset",
    "/api/v1/campaigns/c1/recipients",
    "/api/v1/campaigns/c1/launch",
  ]);
  assert.deepEqual(log[0].body, { name: "Chase", goal: "book", agent_id: "agent-1" });
  assert.equal(log[0].auth, "Bearer jwt-abc");
});

test("callFromAgent dials through the phone endpoint", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([
    { body: { success: true, call_sid: "CA123", provider: "native" } },
  ], log));

  const sf = new Supafone({ accountToken: "jwt-abc" });
  const result = await sf.callFromAgent({ agentId: "agent-1", toNumber: "+15551234567" });

  assert.equal(result.call_sid, "CA123");
  assert.equal(log[0].url.split("api.supafone.ai")[1], "/api/v1/phone/test-call");
  assert.deepEqual(log[0].body, { agent_id: "agent-1", to_number: "+15551234567" });
  await assert.rejects(() => sf.callFromAgent({ agentId: "agent-1" }), SupafoneLabsError);
});

test("live() surfaces in-flight calls with listen + portal links", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([
    {
      body: {
        stats: { queued: 2 },
        calls: [
          { id: "call-live", status: "in_progress" },
          { id: "call-done", status: "completed" },
        ],
      },
    },
  ], log));

  const sf = new Supafone({ accountToken: "jwt-abc" });
  const live = await sf.campaigns.live("c1");

  assert.equal(live.in_flight.length, 1);
  assert.equal(live.in_flight[0].listen_url, "https://app.supafone.ai/app/calls?call=call-live");
  assert.equal(live.portal_url, "https://app.supafone.ai/app/developer?campaign=c1");
});

test("logs in lazily with email/password and retries once on 401", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([
    { body: { token: "jwt-first" } },
    { status: 401, body: { detail: "Token expired" } },
    { body: { token: "jwt-second" } },
    { body: { campaigns: [{ id: "c1" }] } },
  ], log));

  const sf = new Supafone({ accountEmail: "owner@real-domain.io", accountPassword: "hunter22!" });
  const { campaigns } = await sf.campaigns.list();

  assert.equal(campaigns[0].id, "c1");
  assert.ok(log[0].url.endsWith("/api/v1/auth/login"));
  assert.equal(log[0].auth, null);
  assert.equal(log[1].auth, "Bearer jwt-first");
  assert.ok(log[2].url.endsWith("/api/v1/auth/login"));
  assert.equal(log[3].auth, "Bearer jwt-second");
});
