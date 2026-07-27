import { Supafone } from "../sdk-ts/src/index";

declare const process: {
  env: Record<string, string | undefined>;
  exitCode?: number;
};

type RuntimeShape = {
  managed?: boolean;
  key_source?: string;
  telephony?: { mode?: string; provider?: string };
};

type WidgetShape = {
  snippet?: string;
};

type CapsShape = {
  runtimes?: { managed?: string; available?: string[] };
  telephony?: { managed?: { provider?: string } };
  presets?: Array<{ key?: string }>;
  voices?: unknown[];
  api_namespace?: string;
};

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

async function main(): Promise<void> {
  const labsOrApiKey = process.env.SUPAFONE_LABS_API_KEY || process.env.SUPAFONE_API_KEY;
  const supafoneApiKey =
    process.env.SUPAFONE_API_KEY ||
    (labsOrApiKey?.startsWith("sf_live_") || labsOrApiKey?.startsWith("sl_live_")
      ? labsOrApiKey
      : undefined);
  if (!supafoneApiKey) {
    throw new Error("Set SUPAFONE_API_KEY or SUPAFONE_LABS_API_KEY (sf_live_... or sl_live_...).");
  }
  const apiBaseUrl = process.env.SUPAFONE_API_BASE_URL || "https://api.supafone.ai";
  const runId = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
  const agentKey = process.env.SUPAFONE_SMOKE_AGENT_KEY || `smoke-web-intake-${runId}`;
  const presetKey = process.env.SUPAFONE_SMOKE_PRESET_KEY || "general";

  const supafone = new Supafone({
    apiKey: process.env.SUPAFONE_LABS_API_KEY || supafoneApiKey,
    supafoneApiKey,
    supafoneApiBaseUrl: apiBaseUrl,
  });

  console.log(`Supafone API: ${apiBaseUrl}`);
  console.log(`Smoke agent key: ${agentKey}`);

  const capabilities = (await supafone.labs.capabilities()) as CapsShape;
  // Live API embeds presets/voices/runtimes on capabilities (standalone /presets + /voices 404).
  assert(capabilities.runtimes?.managed, "Expected capabilities.runtimes.managed.");
  assert(
    Array.isArray(capabilities.presets) && capabilities.presets.length > 0,
    "Expected capabilities.presets to list industry presets.",
  );
  assert(
    capabilities.presets.some((preset) => preset.key === presetKey),
    `Missing preset ${presetKey} in capabilities.presets.`,
  );
  assert(
    Array.isArray(capabilities.voices) && capabilities.voices.length > 0,
    "Expected capabilities.voices to list managed voices.",
  );
  assert(
    capabilities.telephony?.managed?.provider === "supafone",
    `Expected managed telephony provider supafone, got ${String(capabilities.telephony?.managed?.provider)}`,
  );

  let agent: Awaited<ReturnType<typeof supafone.labs.agents.create>>;
  let created = false;
  try {
    agent = await supafone.labs.agents.create({
      agentKey,
      agentType: "web",
      name: process.env.SUPAFONE_SMOKE_AGENT_NAME || "Smoke web intake agent",
      assistantName: process.env.SUPAFONE_SMOKE_ASSISTANT_NAME || "Alex",
      businessName: process.env.SUPAFONE_SMOKE_BUSINESS_NAME || "Supafone Smoke Test",
      industry: process.env.SUPAFONE_SMOKE_INDUSTRY || "professional_services",
      websiteUrl: process.env.SUPAFONE_SMOKE_WEBSITE_URL || "https://example.com",
      presetKey,
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
    created = true;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    // Trial accounts are capped (often 1 agent). Fall back to list+get.
    if (!/\b402\b|trial plan|Upgrade your plan/i.test(message)) {
      throw err;
    }
    console.log(`Create blocked (${message}). Falling back to existing agent.`);
    const listed = await supafone.labs.agents.list();
    const rows = (listed as { agents?: Array<{ agent_key?: string; agentKey?: string }> }).agents || [];
    assert(rows.length > 0, "Trial create blocked and no existing agents to verify.");
    const existingKey = rows[0].agent_key || rows[0].agentKey;
    assert(existingKey, "Listed agent missing agent_key.");
    agent = await supafone.labs.agents.get(existingKey);
  }

  const resolvedKey = agent.agent?.agent_key || (agent.agent as { agentKey?: string } | undefined)?.agentKey;
  assert(resolvedKey, "Expected agent.agent_key in response.");
  if (created) {
    assert(resolvedKey === agentKey, `Expected agent_key ${agentKey}, got ${String(resolvedKey)}`);
  }

  const runtime = agent.runtime as RuntimeShape | undefined;
  const telephonyMode =
    runtime?.telephony?.mode ||
    (agent.agent as { telephony?: { mode?: string } } | undefined)?.telephony?.mode;
  assert(
    telephonyMode === "supafone_managed" || runtime?.managed === true,
    `Expected Supafone-managed telephony/runtime, got mode=${String(telephonyMode)} managed=${String(runtime?.managed)}`,
  );

  const fetched = await supafone.labs.agents.get(resolvedKey, { agentType: agent.agent?.agent_type || "web" });
  assert(
    fetched.agent.agent_key === resolvedKey,
    `Fetch returned the wrong agent: ${String(fetched.agent.agent_key)}`,
  );

  const widget = (agent.widget || (fetched as { widget?: WidgetShape }).widget) as WidgetShape | undefined;
  if (created) {
    assert(widget?.snippet, "Expected a web widget snippet for newly created web agent.");
  }

  console.log("Smoke test passed.");
  console.log(
    JSON.stringify(
      {
        created,
        agent_key: resolvedKey,
        display_name: agent.agent.display_name,
        runtime_mode: agent.agent.runtime_mode,
        preset_key: agent.agent.preset_key,
        provider_mode: telephonyMode,
        managed_runtime: runtime?.managed,
        widget_snippet: widget?.snippet || null,
      },
      null,
      2,
    ),
  );
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
