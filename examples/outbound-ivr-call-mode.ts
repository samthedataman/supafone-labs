import Supafone, { outboundCallModeReadiness } from "supafone-labs";

const sf = new Supafone({ apiKey: "sf_live_replace_me" });

const readiness = outboundCallModeReadiness(
  { enabled: true },
  {
    provider: "telnyx",
    dtmf: true,
    statePersistence: true,
    humanDetection: true,
    observability: true,
  },
);
if (!readiness.ready) throw new Error(`Outbound IVR adapter is not ready: ${readiness.reasons}`);

await sf.labs.agents.createOutbound({
  name: "Benefits verification",
  outboundCallMode: {
    enabled: true,
    maxDurationSeconds: 180,
    maxKeypresses: 12,
  },
});
