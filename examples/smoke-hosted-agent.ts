import { Supafone } from "../sdk-ts/src/index";

declare const process: { env: Record<string, string | undefined> };

type RuntimeShape = {
  provider_accounts?: {
    mode?: string;
    requires_developer_provider_keys?: boolean;
  };
};

type WidgetShape = {
  snippet?: string;
};

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

const supafoneApiKey =
  process.env.SUPAFONE_API_KEY ||
  (process.env.SUPAFONE_LABS_API_KEY?.startsWith("sf_live_")
    ? process.env.SUPAFONE_LABS_API_KEY
    : undefined);
if (!supafoneApiKey) {
  throw new Error("Set SUPAFONE_API_KEY=sf_live_... to a hosted Supafone agent API key.");
}
const apiBaseUrl = process.env.SUPAFONE_API_BASE_URL || "https://api.supafone.ai";
const runId = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
const agentKey = process.env.SUPAFONE_SMOKE_AGENT_KEY || `smoke-web-intake-${runId}`;

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY || supafoneApiKey,
  supafoneApiKey,
  supafoneApiBaseUrl: apiBaseUrl,
});

console.log(`Supafone API: ${apiBaseUrl}`);
console.log(`Smoke agent key: ${agentKey}`);

const capabilities = await supafone.labs.capabilities();
assert(
  capabilities.api_namespace === "/api/v1/labs",
  `Expected /api/v1/labs namespace, got ${String(capabilities.api_namespace)}`,
);

const presets = await supafone.labs.presets.list();
assert(
  presets.presets.some((preset) => preset.key === "general_intake_receptionist"),
  "Missing general_intake_receptionist preset.",
);

const voices = await supafone.labs.voices.list({ provider: process.env.SUPAFONE_VOICE_PROVIDER || "cartesia" });
assert(voices.total > 0, "Expected at least one Supafone-managed voice.");

const agent = await supafone.labs.agents.create({
  agentKey,
  agentType: "web",
  name: process.env.SUPAFONE_SMOKE_AGENT_NAME || "Smoke web intake agent",
  assistantName: process.env.SUPAFONE_SMOKE_ASSISTANT_NAME || "Alex",
  businessName: process.env.SUPAFONE_SMOKE_BUSINESS_NAME || "Supafone Smoke Test",
  industry: process.env.SUPAFONE_SMOKE_INDUSTRY || "professional_services",
  websiteUrl: process.env.SUPAFONE_SMOKE_WEBSITE_URL || "https://example.com",
  presetKey: "general_intake_receptionist",
  runtimeMode: "multi_stage",
  voice: {
    provider: process.env.SUPAFONE_VOICE_PROVIDER || "cartesia",
    voiceId: process.env.SUPAFONE_VOICE_ID || "Jacqueline",
  },
  labs: {
    enabled: true,
    model: process.env.SUPAFONE_WATCHER_MODEL || "gemma",
  },
  tools: {
    callRouting: true,
    scheduling: true,
    sms: true,
    email: true,
    intakeForms: true,
    firmKnowledge: true,
    voicemail: true,
  },
});

assert(agent.success, "Agent create did not return success=true.");
assert(agent.agent.agent_key === agentKey, `Expected agent_key ${agentKey}, got ${String(agent.agent.agent_key)}`);

const runtime = agent.runtime as RuntimeShape;
assert(runtime.provider_accounts, "Missing provider_accounts in runtime response.");
assert(
  runtime.provider_accounts.mode === "supafone_managed",
  `Expected Supafone-managed providers, got ${String(runtime.provider_accounts.mode)}`,
);
const providerAccounts = runtime.provider_accounts;
assert(
  providerAccounts.requires_developer_provider_keys === false,
  "Expected requires_developer_provider_keys=false.",
);

const fetched = await supafone.labs.agents.get(agentKey, { agentType: "web" });
assert(
  fetched.agent.agent_key === agentKey,
  `Fetch returned the wrong agent: ${String(fetched.agent.agent_key)}`,
);

const widget = agent.widget as WidgetShape | undefined;
assert(widget?.snippet, "Expected a web widget snippet.");

console.log("Smoke test passed.");
console.log(
  JSON.stringify(
    {
      agent_key: agent.agent.agent_key,
      display_name: agent.agent.display_name,
      runtime_mode: agent.agent.runtime_mode,
      preset_key: agent.agent.preset_key,
      provider_mode: providerAccounts.mode,
      requires_developer_provider_keys: providerAccounts.requires_developer_provider_keys,
      widget_snippet: widget.snippet,
    },
    null,
    2,
  ),
);
