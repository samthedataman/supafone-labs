import { test } from "node:test";
import assert from "node:assert/strict";

import Supafone from "../dist/index.js";

function mockFetch(log) {
  return async (url, init) => {
    log.push({ url: String(url), method: init?.method });
    return {
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ events: [], calls: [], count: 0 }),
    };
  };
}

test("calls, activity, and plans use durable account-scoped APIs", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", mockFetch(log));
  const sf = new Supafone({ apiKey: "sf_test" });

  await sf.labs.calls.list({ agencyId: "acct_1", limit: 25, offset: 50 });
  await sf.labs.calls.get("call_1", { agencyId: "acct_1" });
  await sf.labs.calls.delete("call_1", { agencyId: "acct_1" });
  await sf.labs.activity.list({
    agencyId: "acct_1",
    eventType: "watcher.whispered",
    resourceType: "call",
    resourceId: "call_1",
    limit: 10,
    offset: 2,
  });
  await sf.labs.plans.list({ agencyId: "acct_1", limit: 5 });

  assert.deepEqual(log, [
    {
      method: "GET",
      url: "https://api.supafone.ai/api/v1/labs/calls?agency_id=acct_1&limit=25&offset=50",
    },
    {
      method: "GET",
      url: "https://api.supafone.ai/api/v1/labs/calls/call_1?agency_id=acct_1",
    },
    {
      method: "DELETE",
      url: "https://api.supafone.ai/api/v1/labs/calls/call_1?agency_id=acct_1",
    },
    {
      method: "GET",
      url: "https://api.supafone.ai/api/v1/labs/activity?account_id=acct_1&event_type=watcher.whispered&resource_type=call&resource_id=call_1&limit=10&offset=2",
    },
    {
      method: "GET",
      url: "https://api.supafone.ai/api/v1/labs/activity?account_id=acct_1&event_type=studio.plan.created&resource_type=studio_plan&limit=5",
    },
  ]);
});
