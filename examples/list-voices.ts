import { Supafone } from "../sdk-ts/src/index";

declare const process: { env: Record<string, string | undefined> };

const supafoneApiKey =
  process.env.SUPAFONE_API_KEY ||
  (process.env.SUPAFONE_LABS_API_KEY?.startsWith("sf_live_")
    ? process.env.SUPAFONE_LABS_API_KEY
    : undefined);

if (!supafoneApiKey) {
  throw new Error("Set SUPAFONE_API_KEY=sf_live_... to a hosted Supafone agent API key.");
}

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY || supafoneApiKey,
  supafoneApiKey,
  supafoneApiBaseUrl: process.env.SUPAFONE_API_BASE_URL || "https://api.supafone.ai",
});

const provider = process.env.SUPAFONE_VOICE_PROVIDER;
const result = await supafone.labs.voices.list(provider ? { provider } : {});

console.log(`Found ${result.total} Supafone-managed voices`);

for (const voice of result.voices.slice(0, 20)) {
  const id = String(voice.voice_id ?? voice.id ?? voice.key ?? "");
  const name = String(voice.name ?? voice.label ?? voice.display_name ?? id);
  const providerName = String(voice.provider ?? "unknown");
  console.log(`${providerName}: ${name}${id ? ` (${id})` : ""}`);
}
