import { Supafone, type LabsRuntimeConfig, type LabsRuntimeResponse } from "../src/index.js";

const client = new Supafone({ apiKey: "sf_type_test" });
const managed: LabsRuntimeConfig = { provider: "smallest", mode: "supafone_managed" };
const byok: LabsRuntimeConfig = { provider: "openai", mode: "byok", credentials: { apiKey: "fixture" } };
const native: LabsRuntimeResponse = {
  account_id: "account", provider: "smallest", configured: true, connected: true, source: "account",
};
const legacy: LabsRuntimeResponse = {
  account_id: "account", provider: "ultravox", managed: true, byok_connected: false,
};
void client.labs.runtime.get({ provider: "smallest", agencyId: "account" });
void client.labs.runtime.configure(managed);
void client.labs.runtime.configure(byok);
void native;
void legacy;
