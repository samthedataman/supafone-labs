import { test } from "node:test";
import assert from "node:assert/strict";

import Supafone, {
  OUTBOUND_CALL_MODE_BOUNDS,
  OUTBOUND_CALL_MODE_PROVIDER_MATRIX,
  SupafoneLabsError,
  outboundCallModeProviderProfile,
  outboundCallModeReadiness,
} from "../dist/index.js";

function mockFetch(responses, log) {
  return async (url, init) => {
    log.push({
      url: String(url),
      method: init?.method,
      body: init?.body ? JSON.parse(init.body) : undefined,
    });
    const { status = 200, body = {} } = responses.shift() ?? {};
    return { ok: status < 400, status, text: async () => JSON.stringify(body) };
  };
}

const agentResponse = { body: { success: true, agent: { agent_key: "ivr-agent" }, runtime: {} } };

test("outbound call mode is omitted by default and disabled is minimal", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([agentResponse, agentResponse], log));
  const sf = new Supafone({ apiKey: "sf_test" });

  await sf.labs.agents.createOutbound({ name: "Legacy outbound" });
  await sf.labs.agents.createOutbound({
    name: "Disabled outbound",
    outboundCallMode: { enabled: false },
  });

  assert.equal("metadata" in log[0].body, false);
  assert.deepEqual(log[1].body.metadata.outbound_call_mode, { version: 1, enabled: false });
});

test("agent create serializes canonical provider-neutral defaults", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([agentResponse], log));
  const sf = new Supafone({ apiKey: "sf_test" });

  await sf.labs.agents.createOutbound({
    name: "Claims follow-up",
    metadata: { tenant_label: "north" },
    outboundCallMode: {
      enabled: true,
      observability: { metadata: { workflow: "claims" } },
    },
  });

  const { metadata } = log[0].body;
  assert.equal(metadata.tenant_label, "north");
  assert.deepEqual(metadata.outbound_call_mode, {
    version: 1,
    enabled: true,
    initial_mode: "mission",
    ivr_mode: "dynamic",
    transport_scope: "provider_agnostic",
    capability_policy: "fail_closed",
    auto_detect: true,
    dtmf_tool_enabled: true,
    max_duration_seconds: 180,
    max_keypresses: 12,
    repeated_menu_limit: 3,
    no_progress_timeout_seconds: 30,
    human_detection_enabled: true,
    resume_on_human: true,
    observability: {
      enabled: true,
      include_trigger: true,
      include_transitions: true,
      include_termination_reason: true,
      metadata: { workflow: "claims" },
    },
    required_capabilities: ["dtmf", "state_persistence", "human_detection", "observability"],
  });
});

test("canonical bounds reject every value just outside the supported range", () => {
  assert.deepEqual(OUTBOUND_CALL_MODE_BOUNDS, {
    maxDurationSeconds: { default: 180, min: 30, max: 900 },
    maxKeypresses: { default: 12, min: 1, max: 64 },
    repeatedMenuLimit: { default: 3, min: 1, max: 10 },
    noProgressTimeoutSeconds: { default: 30, min: 5, max: 120 },
  });
  const cases = [
    ["maxDurationSeconds", 29],
    ["maxDurationSeconds", 901],
    ["maxKeypresses", 0],
    ["maxKeypresses", 65],
    ["repeatedMenuLimit", 0],
    ["repeatedMenuLimit", 11],
    ["noProgressTimeoutSeconds", 4],
    ["noProgressTimeoutSeconds", 121],
  ];
  for (const [field, value] of cases) {
    const sf = new Supafone({ apiKey: "sf_test" });
    assert.throws(
      () => sf.labs.agents.createOutbound({
        name: "Invalid limits",
        outboundCallMode: { enabled: true, [field]: value },
      }),
      SupafoneLabsError,
    );
  }
});

test("provider aliases cover all six transport families without inferring readiness", () => {
  const expected = {
    supafone_managed: "supafone_managed",
    byo_twilio: "twilio",
    byo_telnyx: "telnyx",
    byo_plivo: "plivo",
    signal_wire: "signalwire",
    custom_sip: "sip_byoc",
  };
  assert.deepEqual(Object.keys(OUTBOUND_CALL_MODE_PROVIDER_MATRIX).sort(), [
    "plivo",
    "signalWire",
    "sipByoc",
    "supafoneManaged",
    "telnyx",
    "twilio",
  ]);
  for (const [alias, family] of Object.entries(expected)) {
    const profile = outboundCallModeProviderProfile(alias);
    assert.equal(profile.transportFamily, family);
    assert.equal(profile.execution, "adapter_runtime_dependent");
    assert.equal(profile.capabilityPolicy, "fail_closed");
  }
});

test("Telnyx can be ready and unsupported or missing adapters fail closed", () => {
  const config = { enabled: true };
  const ready = outboundCallModeReadiness(config, {
    provider: "telnyx",
    dtmf: true,
    statePersistence: true,
    humanDetection: true,
    observability: true,
  });
  assert.equal(ready.ready, true);
  assert.equal(ready.status, "ready");
  assert.equal(ready.transportFamily, "telnyx");

  const unsupported = outboundCallModeReadiness(config, {
    provider: "signalwire",
    dtmf: false,
    statePersistence: true,
    humanDetection: true,
    observability: true,
  });
  assert.equal(unsupported.ready, false);
  assert.equal(unsupported.status, "unsupported");
  assert.deepEqual(unsupported.unsupportedCapabilities, ["dtmf"]);

  const unknown = outboundCallModeReadiness(config, { provider: "twilio" });
  assert.equal(unknown.status, "unknown");
  assert.ok(unknown.missingCapabilities.includes("dtmf"));

  const unlistedReady = outboundCallModeReadiness(config, {
    provider: "unlisted_adapter",
    dtmf: true,
    statePersistence: true,
    humanDetection: true,
    observability: true,
  });
  assert.equal(unlistedReady.ready, true);
  assert.equal(unlistedReady.transportFamily, "unknown");
});

test("agent update and lifecycle routes preserve metadata and canonicalize mode", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([
    { body: { success: true } },
    { body: { ready: true } },
    { body: { success: true, lifecycle: "active" } },
    { body: { success: true, lifecycle: "paused" } },
  ], log));
  const sf = new Supafone({ apiKey: "sf_test" });

  await sf.labs.agents.update("agent/one", {
    metadata: { owner: "ops" },
    outboundCallMode: { enabled: true, maxKeypresses: 20 },
  }, { agencyId: "agency-1" });
  await sf.labs.agents.readiness("agent/one", { agencyId: "agency-1" });
  await sf.labs.agents.activate("agent/one", { agencyId: "agency-1" });
  await sf.labs.agents.pause("agent/one", { agencyId: "agency-1" });

  assert.deepEqual(log.map((entry) => [entry.method, entry.url.split("api.supafone.ai")[1]]), [
    ["PATCH", "/api/v1/labs/agents/agent%2Fone?agency_id=agency-1"],
    ["GET", "/api/v1/labs/agents/agent%2Fone/readiness?agency_id=agency-1"],
    ["POST", "/api/v1/labs/agents/agent%2Fone/activate?agency_id=agency-1"],
    ["POST", "/api/v1/labs/agents/agent%2Fone/pause?agency_id=agency-1"],
  ]);
  assert.equal(log[0].body.metadata.owner, "ops");
  assert.equal(log[0].body.metadata.outbound_call_mode.max_keypresses, 20);
});

test("campaign create and update persist mode under settings", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([
    { body: { campaign: { id: "campaign-1" } } },
    { body: { campaign: { id: "campaign-1" } } },
    { body: { campaign: { id: "campaign-1" } } },
  ], log));
  const sf = new Supafone({ accountToken: "jwt-test" });

  await sf.campaigns.create({
    name: "IVR follow-up",
    settings: { timezone: "America/New_York" },
    outboundCallMode: { enabled: true },
  });
  await sf.campaigns.update("campaign-1", {
    settings: { cadence_label: "weekday" },
    outboundCallMode: { enabled: false },
  });

  assert.deepEqual(log[0].body, { name: "IVR follow-up", goal: "book" });
  assert.equal(log[1].body.settings.timezone, "America/New_York");
  assert.equal(log[1].body.settings.outbound_call_mode.transport_scope, "provider_agnostic");
  assert.deepEqual(log[2].body.settings, {
    cadence_label: "weekday",
    outbound_call_mode: { version: 1, enabled: false },
  });
});

test("campaign create without settings keeps the legacy single request", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch([
    { body: { campaign: { id: "campaign-1" } } },
  ], log));
  const sf = new Supafone({ accountToken: "jwt-test" });

  await sf.campaigns.create({ name: "Legacy" });

  assert.equal(log.length, 1);
  assert.deepEqual(log[0].body, { name: "Legacy", goal: "book" });
});
