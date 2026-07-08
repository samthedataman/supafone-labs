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

const agent = await supafone.labs.agents.createOutboundWithNumber({
  agentKey: "sales-speed-to-lead",
  agentType: "campaign",
  name: "Speed-to-lead sales agent",
  assistantName: "Jordan",
  businessName: "Supafone Demo Team",
  industry: "sales",
  websiteUrl: "https://supafone.ai",
  direction: "outbound",
  number: { search: { areaCode: "415" } },
  goal: "Call new leads quickly, qualify intent, handle objections, and book a meeting or cleanly hand off.",
  voice: {
    provider: "cartesia",
    voiceId: "Jacqueline",
  },
  labs: {
    enabled: true,
    voiceWatcher: true,
    model: "gemma",
    label: "Supafone Pro",
  },
  tools: {
    callRouting: true,
    scheduling: true,
    sms: true,
    email: true,
    voicemail: true,
    customTools: [
      {
        id: "crm_lookup",
        name: "CRM lookup",
        description: "Look up the prospect, lead source, owner, and last touch before calling.",
      },
      {
        id: "meeting_booked",
        name: "Meeting booked",
        description: "Mark the lead as booked after the caller confirms a meeting time.",
      },
    ],
  },
  ultravox: {
    vadSettings: {
      turnEndpointDelay: "0.256s",
      minimumTurnDuration: "0s",
      minimumInterruptionDuration: "0.40s",
      frameActivationThreshold: 0.16,
    },
    firstSpeakerSettings: {
      user: {},
    },
    initialState: {
      campaign_goal: "book_meeting",
      call_coach: "enabled",
    },
    maxDuration: "480s",
  },
});

console.log("Created sales agent:", agent.agent.agent_key);
console.log("Assigned caller ID:", agent.number?.number.phone_number);
console.log("Supafone Pro:", agent.runtime?.labs);
