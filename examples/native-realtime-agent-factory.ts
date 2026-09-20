import { Supafone } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_API_KEY! });
const agent = await supafone.labs.agents.createInbound({
  agentKey: "native-realtime-intake",
  name: "Native realtime intake",
  realtime: { provider: "openai", model: "gpt-realtime-2.1", voice: "marin" },
});
const preview = await supafone.labs.agents.testCall(agent.agent.agent_key!);
console.log(preview.browser_session.transport);
