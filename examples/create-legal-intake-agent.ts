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
  agentKey: "legal-intake",
  name: "Legal intake agent",
  assistantName: "Maya",
  businessName: "Wallace Injury Group",
  industry: "legal",
  websiteUrl: "https://example-law-firm.com",
  number: { search: { areaCode: "917" } },
  goal: "Qualify new legal callers, capture matter details, and route urgent matters to the right person.",
  greeting: "Thanks for calling Wallace Injury Group. I can collect a few details and get you to the right next step.",
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
    intakeForms: true,
    firmKnowledge: true,
    voicemail: true,
    emergencyEscalation: true,
  },
  metadata: {
    example: "legal-intake",
    required_outcomes: ["matter_type", "urgency", "callback_number", "next_step"],
  },
});

console.log("Created legal intake agent:", agent.agent.agent_key);
console.log("Assigned number:", agent.number?.number.phone_number);
console.log("Runtime:", agent.runtime);
