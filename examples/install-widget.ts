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

const agent = await supafone.labs.agents.create({
  agentKey: "website-intake",
  agentType: "web",
  name: "Website intake agent",
  assistantName: "Alex",
  businessName: "Northline Studio",
  industry: "professional_services",
  websiteUrl: "https://example.com",
  presetKey: "general_intake_receptionist",
  runtimeMode: "multi_stage",
  voice: {
    provider: "cartesia",
    voiceId: "Jacqueline",
  },
  labs: {
    enabled: true,
    model: "gemma",
  },
  tools: {
    scheduling: true,
    sms: true,
    email: true,
    intakeForms: true,
    firmKnowledge: true,
  },
});

if (!agent.widget?.snippet) {
  throw new Error("The API did not return a widget snippet for this agent.");
}

console.log("Paste this before </body> on your site:");
console.log(agent.widget.snippet);
