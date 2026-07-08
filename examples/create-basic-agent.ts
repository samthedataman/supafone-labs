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

const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "basic-intake",
  name: "Basic intake agent",
  assistantName: "Alex",
  businessName: "Northline Studio",
  industry: "professional_services",
  websiteUrl: "https://example.com",
  number: { search: { areaCode: "415" } },
  voice: {
    provider: "cartesia",
    voiceId: "Jacqueline",
  },
  labs: {
    enabled: true,
    model: "gemma",
  },
  tools: {
    callRouting: true,
    scheduling: true,
    sms: true,
    email: true,
    firmKnowledge: true,
    voicemail: true,
    emergencyEscalation: true,
  },
});

console.log("Created agent:", agent.agent.agent_key);
console.log("Assigned number:", agent.number?.number.phone_number);
console.log("Widget snippet:", agent.widget?.snippet);
