# Quickstart

```bash
pip install supafone-labs
```

## 1. Supercharge an agent (one line)

```python
import supafone_labs

brain = supafone_labs.supercharge(my_agent)     # provider auto-detected
```

Runs with **no API key** using the built-in fake provider, so you can see it work
immediately, then swap in a real provider via `ANTHROPIC_API_KEY`.

## 1b. Or create a hosted Supafone agent from REST, Python, TypeScript, or MCP

If you want Supafone to host the agent, use the public REST API directly or a
matching SDK/MCP client. This creates an Ultravox-backed Supafone agent with a
Supafone-managed phone number, managed voices, multistage state, tools,
recordings, transcripts, and optional Supafone Pro watcher. You do not need
Ultravox, Twilio, Cartesia, Inworld, ElevenLabs, or Deepgram keys in the default
path.

There are two main features:

- **Agent Factory** creates a complete hosted agent with managed defaults, so
  developers do not need their own agent-platform, telephony, TTS, STT, or LLM
  keys to get started.
- **Self-healing watcher** attaches Supafone Labs to a hosted or existing agent
  and sends silent corrective directives only when `labs.enabled` is on.

Think of this as the full agent-building framework path: describe the job,
review the generated prompts and executable stages when needed, choose a voice
and tools, and create a durable agent profile that syncs to the normal Supafone
account.

```bash
npm i supafone-labs
export SUPAFONE_TOKEN=sl_live_...
```

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_TOKEN!,
  voiceWatcher: true, // default on — provisions agents under the Voice Watcher framework
});

const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "medivoice-intake",
  name: "MediVoice intake",
  assistantName: "Maya",
  businessName: "MediVoice",
  description: "Answer new inquiries, capture the facts that matter, and book or route the next step.",
  websiteUrl: "https://medivoice.org",
  number: { search: { areaCode: "787" } },
  voice: { provider: "cartesia", voiceId: "Jacqueline" },
  labs: { enabled: true, model: "gemma" },
  tools: {
    callRouting: true,
    scheduling: true,
    sms: true,
    email: true,
    firmKnowledge: true,
    voicemail: true,
  },
});

console.log(agent.agent.agent_key, agent.call_plan?.call_stages);
```

REST uses the same contract; no TypeScript runtime is required:

```bash
curl https://api.supafone.ai/api/v1/labs/agent-plans \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description":"Answer new inquiries and book the right next step","direction":"inbound","stage_count":5}'
```

Python uses `supafone.generate_call_stages(...)` and
`supafone.labs.agents.create_inbound(...)`; MCP exposes
`generate_call_stages` and the hosted-agent creation tools.

For outbound sales or speed-to-lead workflows, use the matching helper:

```ts
const salesAgent = await supafone.labs.agents.createOutboundWithNumber({
  agentKey: "medivoice-sales",
  name: "MediVoice sales team",
  assistantName: "Maya",
  description: "Call warm, consented leads, understand fit, and book the next step without pressure.",
  websiteUrl: "https://medivoice.org",
  number: { search: { areaCode: "787" } },
  labs: { enabled: true, model: "gemma" },
});
```

Teams that already own provider accounts can configure BYOK later. Keep the
three lanes separate: agent/provider stack, telephony, and TTS.

```ts
await supafone.labs.telephony.configure({
  mode: "byok",
  provider: "twilio",
  credentials: {
    accountSid: process.env.TWILIO_ACCOUNT_SID!,
    authToken: process.env.TWILIO_AUTH_TOKEN!,
    fromNumber: "+14155550123",
  },
});
```

```ts
await supafone.labs.agents.createOutbound({
  agentKey: "byok-speed-to-lead",
  name: "BYOK speed to lead",
  byok: {
    agentProvider: { provider: "ultravox", apiKey: process.env.ULTRAVOX_API_KEY },
    telephony: {
      mode: "byok",
      provider: "telnyx",
      credentials: { apiKey: process.env.TELNYX_API_KEY }
    },
    tts: { provider: "cartesia", apiKey: process.env.CARTESIA_API_KEY }
  },
  labs: { enabled: true, mode: "byok", managedInfrastructure: false }
});
```

To verify the full hosted-agent path, run the smoke test:

```bash
cd supafone-labs
SUPAFONE_TOKEN=sl_live_... \
SUPAFONE_API_BASE_URL=https://api.supafone.ai \
npx tsx examples/smoke-hosted-agent.ts
```

It discovers capabilities, presets, and voices, creates a web intake agent,
fetches it back, confirms `runtime.telephony.mode` is `supafone_managed` and the
runtime is managed (`runtime.managed === true`, no developer Ultravox key
required), and prints the widget snippet.

Use `supafone.labs.voices.list()` to show available voice choices, and
`supafone.labs.presets.list()` to show the stage presets before creating the
agent.

## 2. Give it a live data feed

The oracle is only as smart as what it can see. Snap in context sources:

```python
feed = supafone_labs.Feed(
    context=[
        supafone_labs.CallerHistory(db),       # who is this, prior calls
        supafone_labs.Knowledge(vectorstore),  # firm/product knowledge (RAG)
        supafone_labs.CRM(crm_client),         # case / lead data
    ],
    guardrails=["don't quote fees", "no legal advice"],
)

brain = supafone_labs.supercharge(my_agent, feed=feed, scenario="legal_intake")
```

## 3. Own the loop (webhook / realtime)

```python
sm = supafone_labs.SupafoneLabs(provider="gpt_realtime", feed=feed)

async def on_event(raw_event):
    inject = await sm.observe(raw_event)   # -> silent instruction to send back, or None
    if inject:
        await my_agent.send_system(inject)
```

## 4. Let it learn

Every recorded call becomes training data. Run gradient descent on your prompts from the
replay corpus:

```python
from supafone_labs import get_optimizer

optimizer = get_optimizer("textgrad")
improved = optimizer.optimize(program, dataset, steps=10)   # prompts that win more
```
