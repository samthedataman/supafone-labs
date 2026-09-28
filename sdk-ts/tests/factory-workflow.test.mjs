import { test } from "node:test";
import assert from "node:assert/strict";
import Supafone from "../dist/index.js";

function capture(t) {
  const calls = [];
  t.mock.method(globalThis, "fetch", async (url, init) => {
    calls.push({ url: String(url), method: init.method, body: JSON.parse(init.body) });
    return { ok: true, status: 200, text: async () => JSON.stringify({ success: true }) };
  });
  return { client: new Supafone({ apiKey: "sf_test" }), calls };
}

const workflow = {
  name: "Booking team", realtime: { provider: "google", model: "gemini-3.1-flash-live-preview" },
  captureFields: ["name", "reference"],
  manager: { enabled: true, reasoning: "supervisor", maxTasks: 6, maxParallel: 2, timeoutSeconds: 5 },
  agentTeam: { enabled: true, fallbackMemberId: "booker", members: [
    { id: "booker", stageKeys: ["book"], instructions: "Consult the calendar.", tools: ["check_availability"] },
  ] },
  runtimeRouting: { enabled: true, allowedModels: [{ provider: "xai", model: "grok-voice-latest", voice: "eve" }],
    maxHandoffs: 1, recoverOnDisconnect: false },
  recording: { enabled: true, transcribe: true },
  callStages: [
    { key: "capture", name: "Capture", temperature: 0.2, tools: ["save_lead"], nextStages: ["book", "decline"],
      requirements: { requiredFields: ["name"], successfulTools: [] } },
    { key: "decline", name: "Decline", tools: [], nextStages: [] },
    { key: "book", name: "Book", tools: ["book_appointment"], role: "scheduling", specialistId: "booker", nextStages: [],
      requirements: { successfulTools: ["book_appointment"] } },
  ],
};

test("create and patch transmit workflow gates, teams, manager and routing", async (t) => {
  const { client, calls } = capture(t);
  await client.labs.agents.create(workflow);
  await client.labs.agents.update("booker", workflow);
  for (const { body } of calls) {
    assert.deepEqual(body.manager, { enabled: true, reasoning: "supervisor", max_tasks: 6, max_parallel: 2, timeout_seconds: 5 });
    assert.deepEqual(body.agent_team.members[0].stage_keys, ["book"]);
    assert.deepEqual(body.capture_fields, ["name", "reference"]);
    assert.deepEqual(body.recording, { enabled: true, transcribe: true });
    assert.equal(body.runtime_routing.recover_on_disconnect, false);
    assert.deepEqual(body.call_stages[0].requirements, { required_fields: ["name"], successful_tools: [] });
    assert.deepEqual(body.call_stages[1].next_stages, []);
    assert.deepEqual(body.call_stages[1].tools, []);
    assert.equal(body.call_stages[2].specialist_id, "booker");
  }
});

test("patch preserves explicit disabled settings and does not add defaults", async (t) => {
  const { client, calls } = capture(t);
  await client.labs.agents.update("booker", {
    manager: false, recording: { enabled: false, transcribe: false }, runtime_routing: { enabled: false, allowed_models: [] },
  });
  assert.deepEqual(calls[0].body, {
    manager: false, recording: { enabled: false, transcribe: false }, runtime_routing: { enabled: false, allowed_models: [] },
  });
});

test("plan endpoint normalizes explicit stages and omits credential profiles", async (t) => {
  const { client, calls } = capture(t);
  await client.labs.agents.plan({ ...workflow, supervisor: { mode: "byok", apiKey: "must-not-enter-planner" } });
  assert.deepEqual(calls[0].body.call_stages[1].next_stages, []);
  assert.deepEqual(calls[0].body.call_stages[0].requirements.required_fields, ["name"]);
  assert.equal("manager" in calls[0].body, false);
  assert.equal(JSON.stringify(calls).includes("must-not-enter-planner"), false);
});

test("boolean recording, timezone and language permissions preserve explicit values", async (t) => {
  const { client, calls } = capture(t);
  await client.labs.agents.update("booker", { recording: false, timezone: "America/New_York", timeAwareness: false,
    runtimeRouting: { enabled: true, allowedLanguages: ["en"] } });
  assert.deepEqual(calls[0].body, { recording: false, timezone: "America/New_York", time_awareness: false,
    runtime_routing: { enabled: true, allowed_languages: ["en"] } });
});
