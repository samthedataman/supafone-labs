import { Supafone } from "../sdk-ts/src/index";

declare const process: {
  env: Record<string, string | undefined>;
  exitCode?: number;
};

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

  const supafone = new Supafone({
    apiKey: process.env.SUPAFONE_LABS_API_KEY || supafoneApiKey,
    supafoneApiKey,
    supafoneApiBaseUrl: process.env.SUPAFONE_API_BASE_URL || "https://api.supafone.ai",
  });

  // Live /api/v1/labs/voices 404s; catalog lives on capabilities.
  const capabilities = await supafone.labs.capabilities();
  const voices = (capabilities as { voices?: Array<Record<string, unknown>> }).voices || [];
  const providerFilter = process.env.SUPAFONE_VOICE_PROVIDER;

  const filtered = providerFilter
    ? voices.filter((voice) => String(voice.provider ?? "").toLowerCase() === providerFilter.toLowerCase())
    : voices;

  console.log(`Found ${filtered.length} Supafone-managed voices`);

  for (const voice of filtered.slice(0, 20)) {
    const id = String(voice.voice_id ?? voice.id ?? voice.key ?? "");
    const name = String(voice.name ?? voice.label ?? voice.display_name ?? id);
    const providerName = String(voice.provider ?? "unknown");
    console.log(`${providerName}: ${name}${id ? ` (${id})` : ""}`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
