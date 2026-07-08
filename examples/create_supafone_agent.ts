import { Supafone } from "../sdk-ts/src/index";

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

const capabilities = await supafone.labs.capabilities();
console.log("Default contract:", capabilities.default_agent_contract);

const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "medivoice-intake",
  name: "MediVoice intake",
  assistantName: "Maya",
  businessName: "MediVoice",
  industry: "healthcare",
  websiteUrl: "https://medivoice.org",
  number: { search: { areaCode: "787" } },
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
  ultravox: {
    vadSettings: {
      turnEndpointDelay: "0.384s",
      minimumTurnDuration: "0s",
      frameActivationThreshold: 0.1,
      minimumInterruptionDuration: "0.25s",
    },
    firstSpeakerSettings: {
      agent: { uninterruptible: false },
    },
  },
});

console.log("Created agent:", agent.agent.agent_key);
console.log("Assigned number:", agent.number?.number.phone_number);
console.log("Runtime:", agent.runtime);
console.log("Widget snippet:", agent.widget?.snippet);
