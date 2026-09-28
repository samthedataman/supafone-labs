import type { CreateLabsAgentRequest, UpdateLabsAgentRequest } from "../src/index.js";

const create: CreateLabsAgentRequest = {
  name: "Booking team", captureFields: ["name"],
  manager: { enabled: true, reasoning: "managed", model: "supafone-manager", maxTasks: 4 },
  agentTeam: { members: [{ id: "booker", stageKeys: ["booking"], tools: ["book_appointment"] }] },
  runtimeRouting: { enabled: true, allowedModels: [{ provider: "smallest", model: "hydra-v1.1" }], maxHandoffs: 1 },
  recording: { enabled: true, transcribe: true },
  callStages: [{ name: "Booking", key: "booking", requirements: { successfulTools: ["book_appointment"] }, specialistId: "booker" }],
};
const update: UpdateLabsAgentRequest = { manager: false, agent_team: { enabled: false }, capture_fields: ["name"] };
void create;
void update;
