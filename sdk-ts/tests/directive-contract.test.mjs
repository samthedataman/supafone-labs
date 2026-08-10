import { test } from "node:test";
import assert from "node:assert/strict";

import Supafone from "../dist/index.js";

function oracleFetch(log, text) {
  return async (url, init) => {
    log.push({ url: String(url), body: JSON.parse(init.body) });
    return {
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ text, model: "supafone-labs-oracle" }),
    };
  };
}

const response = JSON.stringify({
  empathy_directive: "Slow down and acknowledge that the caller is worried.",
  tactical_directive: "Confirm the preferred callback time before closing.",
  surface_facts: ["The caller requested a callback after 5 PM", "Caller sounded worried"],
  guardrails: ["Do not promise scheduling"],
  language: "en",
  confidence: 0.86,
  kind: "mixed",
});

test("structured whisper gives developers field-level control", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", oracleFetch(log, response));
  const sf = new Supafone({ apiKey: "sl_test" });

  const directive = await sf.whisperStructured("caller: Please call me after five.", {
    directiveContract: {
      empathyDirective: { enabled: false },
      tacticalDirective: { instructions: "Use a direct command.", maxChars: 18 },
      surfaceFacts: { maxItems: 1, itemMaxChars: 12 },
      guardrails: { enabled: false },
      languageMode: "fixed",
      fixedLanguage: "es",
      allowedKinds: ["mixed"],
      confidenceThreshold: 0.8,
      operatorGuardrails: ["Never claim a callback is booked without tool confirmation"],
    },
  });

  assert.deepEqual(directive, {
    empathy_directive: "",
    tactical_directive: "Confirm the prefer",
    surface_facts: ["The caller r"],
    guardrails: ["Never claim a callback is booked without tool confirmation"],
    language: "es",
    confidence: 0.86,
    kind: "mixed",
  });
  const system = log[0].body.messages[0].content;
  assert.match(system, /Developer directive contract/);
  assert.match(system, /Use a direct command/);
  assert.match(system, /Never claim a callback is booked/);
});

test("structured whisper confidence gate and transform can suppress output", async (t) => {
  const log = [];
  t.mock.method(globalThis, "fetch", oracleFetch(log, response));
  const sf = new Supafone({ apiKey: "sl_test" });

  const low = await sf.directive("caller: Call later", {
    directiveContract: { confidenceThreshold: 0.9 },
  });
  assert.equal(low, null);

  const suppressed = await sf.directive("caller: Call later", {
    transform: () => null,
  });
  assert.equal(suppressed, null);
});
