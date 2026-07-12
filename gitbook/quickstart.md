# 🚀 Quickstart

This page shows both Supafone Labs paths: hosted complete agents and
bring-your-stack supervision.

## 1. Install

```bash
pip install "supafone-labs[all]"
npm i supafone-labs
```

## 2. Get a Key

One `sl_` Labs key is all you need — since 0.4.4 it authenticates on **both**
APIs ([one-key auth](api-keys-and-auth.md)): Labs Cloud
(`api.labs.supafone.ai`) natively, and the product API (`api.supafone.ai`) via
key introspection, as long as an app.supafone.ai account exists with the same
email.

```bash
curl -X POST https://api.labs.supafone.ai/v1/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com"}'

export SUPAFONE_TOKEN=sl_live_...   # one env var: MCP + both SDKs
```

That one `sl_` key is the default for everything below. For hosted-agent-only
setups you can optionally still mint a scoped `sf_live_...` key from the Supafone
account-admin flow and point it at `https://api.supafone.ai` — but the `sl_` key
already covers that surface, so it is the exception, not the default.

## 3. Create a Hosted Inbound Agent

TypeScript:

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_TOKEN!, // sl_ key — cross-fills both surfaces
  voiceWatcher: true, // default on — provisions agents under the Voice Watcher framework; set false for a raw agent
});

const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake",
  name: "Northline intake",
  assistantName: "Maya",
  businessName: "Northline",
  websiteUrl: "https://northline.example",
  number: {
    search: { areaCode: "415" },
    numberStrategy: "default_pool"
  },
  voice: { provider: "cartesia", voiceId: "Jacqueline" },
  labs: { enabled: true, model: "gemma" },
  tools: {
    callRouting: true,
    scheduling: true,
    sms: true,
    email: true,
    firmKnowledge: true,
    voicemail: true
  }
});

console.log(agent.agent.agent_key);
console.log(agent.number?.number.phone_number);
console.log(agent.widget?.snippet);
```

The default pool is the safe starting point. Use `numberStrategy: "dedicated"`
or `numberStrategy: "premium"` only after the customer explicitly chooses a paid
reserved number.

Python:

```python
from supafone_labs import Supafone

supafone = Supafone(api_key="sl_live_...", voice_watcher=True)  # one key; watcher on by default

agent = supafone.labs.agents.create_inbound_with_number({
    "agentKey": "northline-intake",
    "name": "Northline intake",
    "assistantName": "Maya",
    "businessName": "Northline",
    "websiteUrl": "https://northline.example",
    "number": {
        "search": {"areaCode": "415"},
        "numberStrategy": "default_pool",
    },
    "voice": {"provider": "cartesia", "voiceId": "Jacqueline"},
    "labs": {"enabled": True, "model": "gemma"},
    "tools": {
        "callRouting": True,
        "scheduling": True,
        "sms": True,
        "email": True,
        "firmKnowledge": True,
        "voicemail": True,
    },
})

print(agent["agent"]["agent_key"])
print(agent.get("number", {}).get("number", {}).get("phone_number"))
```

## 4. Supervise an Existing Agent

```python
import supafone_labs

brain = supafone_labs.supercharge(
    my_agent,
    scenario="legal_intake",
)

result = await brain.observe(raw_platform_event)

if result.actions:
    await my_agent.deliver(result.actions[0])
```

With `SUPAFONE_LABS_API_KEY=sl_live_...`, the oracle, TTS, and STT use Labs
Cloud. Without it, the SDK can run with your own vendor keys or offline fake
providers for tests.

## 5. Check Balance and Logs

```bash
curl https://api.labs.supafone.ai/v1/billing/balance \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"

curl https://api.labs.supafone.ai/v1/logs?limit=20 \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"
```

## 6. Smoke Test Hosted Agents

```bash
cd supafone-labs
SUPAFONE_API_KEY=sl_live_... \
SUPAFONE_API_BASE_URL=https://api.supafone.ai \
npx tsx examples/smoke-hosted-agent.ts
```

The smoke test checks capabilities, presets, voices, agent creation, fetch by
key, Supafone-managed providers, no required developer provider keys, and a web
widget snippet.

Next: [SDK Parity](sdk-parity.md), [Agent Factory](agent-factory.md),
[Voices and Previews](voices-and-previews.md), and [Log Streaming](log-streaming.md).
