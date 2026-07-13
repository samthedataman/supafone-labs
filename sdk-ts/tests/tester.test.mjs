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

test("tester.gradeAgent starts a provider-neutral authorized PSTN test", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([
    { body: { session_id: "ts_123", status: "dialing", mode: "phone_grader" } },
  ], log));

  const sf = new Supafone({ apiKey: "sl_test" });
  const result = await sf.tester.gradeAgent({
    toNumber: "+14155550100",
    scenario: "language_switch",
    agentLabel: "grok-agent",
    aiProvider: "grok",
    telephonyProvider: "telnyx",
    authorized: true,
  });

  assert.equal(result.session_id, "ts_123");
  assert.equal(log[0].url, "https://api.labs.supafone.ai/v1/tester/call");
  assert.equal(log[0].auth, "Bearer sl_test");
  assert.deepEqual(log[0].body, {
    to_number: "+14155550100",
    scenario: "language_switch",
    agent_label: "grok-agent",
    ai_provider: "grok",
    telephony_provider: "telnyx",
    authorized: true,
  });
});

test("tester.gradeAgent rejects missing permission and non-E.164 targets", () => {
  const sf = new Supafone({ apiKey: "sl_test" });
  assert.throws(
    () => sf.tester.gradeAgent({ toNumber: "+14155550100", authorized: false }),
    SupafoneLabsError,
  );
  assert.throws(
    () => sf.tester.gradeAgent({ toNumber: "415-555-0100", authorized: true }),
    SupafoneLabsError,
  );
});

test("tester.wait returns a terminal transcript and verdict", async () => {
  const sf = new Supafone({ apiKey: "sl_test" });
  sf.tester.session = async () => ({
    status: "done",
    scenario: "price_probe",
    turns: 2,
    transcript: [{ role: "agent", text: "Hello" }],
    verdict: { passed: true, score: 0.94 },
    target: { ai_provider: "gpt_realtime", telephony_provider: "twilio" },
  });

  const result = await sf.tester.wait("ts_123", { timeoutMs: 1_000 });
  assert.equal(result.verdict.score, 0.94);
  assert.equal(result.target.ai_provider, "gpt_realtime");
});
