# Outbound Call Campaigns

Supafone campaigns coordinate consented outbound voice and email sequences
around an owned voice agent. Campaigns are different from browser WebRTC calls
and one-off PSTN calls: they maintain recipients, cadence state, activity,
signing links, and live monitoring as a durable workflow.

## Choose the correct API

| Goal | TypeScript | Python |
| --- | --- | --- |
| Test an agent in the browser | `startWebRtcCall()` | `start_webrtc_call()` |
| Dial one phone immediately | `callFromAgent()` | `call_from_agent()` |
| Run a recipient campaign | `campaigns.*` | `campaigns.*` |
| Grade an existing phone agent | `tester.gradeAgent()` | `tester.grade_agent()` |

## Authentication

Campaign methods use the Supafone product API. A linked `sl_live_...` key can
be supplied as `apiKey`/`SUPAFONE_TOKEN`; account JWT or email/password auth is
also supported. Keep campaign credentials on a trusted server or internal
control panel.

## Complete TypeScript flow

```ts
import { Supafone } from "supafone-labs";

const sf = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN! });

// 1. Select an owned outbound-capable agent.
const { agents } = await sf.listVoiceAgents();
const agentId = String(agents[0].id);

// 2. Create and configure the campaign.
const { campaign } = await sf.campaigns.create({
  name: "August intake follow-up",
  goal: "book",
  agentId,
});
await sf.campaigns.applyPreset(campaign.id, "win_back");

// 3. Add only recipients with documented outreach consent.
await sf.campaigns.addRecipients(campaign.id, [
  {
    name: "Jane Doe",
    phone: "+14155550100",
    email: "jane@example.com",
    outreach_consent: "yes",
  },
]);

// 4. Launching starts real provider activity.
await sf.campaigns.launch(campaign.id);

// 5. Monitor calls and growing transcripts.
const live = await sf.campaigns.live(campaign.id);
for (const call of live.in_flight) {
  console.log(call.listen_url);
  const detail = await sf.campaigns.getCall(call.id);
  console.log(detail.call);
}

// 6. Stop future campaign dispatches when needed.
await sf.campaigns.pause(campaign.id);
```

## Complete Python flow

```python
from supafone_labs import Supafone

sf = Supafone()  # SUPAFONE_TOKEN=sl_live_...

agents = sf.list_voice_agents()["agents"]
created = sf.campaigns.create(
    name="August intake follow-up",
    goal="book",
    agent_id=agents[0]["id"],
)
campaign_id = created["campaign"]["id"]

sf.campaigns.apply_preset(campaign_id, "win_back")
sf.campaigns.add_recipients(campaign_id, [
    {
        "name": "Jane Doe",
        "phone": "+14155550100",
        "email": "jane@example.com",
        "outreach_consent": "yes",
    }
])
sf.campaigns.launch(campaign_id)

live = sf.campaigns.live(campaign_id)
for call in live["in_flight"]:
    print(call["listen_url"])
    print(sf.campaigns.get_call(call["id"]))

sf.campaigns.pause(campaign_id)
```

## Campaign-as-code

Use one YAML or JSON document when campaigns must be portable between client
workspaces:

```yaml
slug: august-intake-follow-up
name: August intake follow-up
goal: book
agent: northline-outbound
branding:
  url: https://northline.example
intake_form:
  description: Follow-up intake and appointment request
  industry: legal
recipients:
  - name: Jane Doe
    phone: "+14155550100"
    consent: yes
```

```ts
const report = await sf.campaigns.validateConfig(yaml);
if (!report.valid) throw new Error(report.errors.join("\n"));

const applied = await sf.campaigns.applyConfig(yaml, { launch: false });
console.log(applied.campaign.id);

const exported = await sf.campaigns.exportConfig(applied.campaign.id);
console.log(exported.config);
```

`launch: true` starts real calls/emails. Validate and review the generated
document before using that option.

## E-sign and completion

Campaigns can upload a signing PDF, detect fields, save explicit placements,
and create recipient-specific signing links:

```ts
const uploaded = await sf.campaigns.uploadSigningDocument(
  campaign.id,
  pdfBytes,
  "retainer.pdf",
);

await sf.campaigns.setSignatureFields(campaign.id, uploaded.detected_fields);
const signed = await sf.campaigns.createSignLink(campaign.id, recipientId);
console.log(signed.link);
```

Provider completion events remain authoritative. A click or AI inference is
not equivalent to a completed signature.

## Production guardrails

- Add only recipients with the required consent for every enabled channel.
- Use E.164 phone numbers and a caller ID owned or authorized by the account.
- Apply business hours, quiet hours, calling windows, opt-out handling, and
  jurisdiction-specific requirements in campaign configuration.
- Treat `launch()` and `applyConfig(..., {launch: true})` as production writes.
- Poll `live()` for active calls and use `getCall()` for the latest transcript;
  do not infer call success from the launch response alone.
- Pause a campaign before materially changing its agent, script, cadence, or
  signing document.

## Lifecycle

```text
agent selected
     ↓
campaign created → preset/config applied
     ↓
consented recipients added
     ↓
launch → cadence dispatches calls/email
     ↓
live activity + transcripts + outcomes
     ↓
signing/completion events and follow-up
     ↓
pause or complete
```
