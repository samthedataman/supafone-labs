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
  agentKey: "medical-receptionist",
  name: "Medical receptionist",
  assistantName: "Sam",
  businessName: "MediVoice Clinic",
  industry: "healthcare",
  websiteUrl: "https://medivoice.org",
  number: { search: { areaCode: "787" } },
  presetKey: "medivoice_medical_receptionist",
  runtimeMode: "multi_stage",
  goal: "Answer patient calls, collect safe intake details, route urgent issues, and book or message the clinic.",
  voice: {
    provider: "inworld",
    voiceId: "Ashley",
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
    example: "medical-receptionist",
    compliance_note: "Do not provide medical advice, diagnosis, or medication guidance.",
  },
});

console.log("Created medical receptionist:", agent.agent.agent_key);
console.log("Assigned number:", agent.number?.number.phone_number);
console.log("Widget snippet:", agent.widget?.snippet);
