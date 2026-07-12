# 🧑‍💻 Developer Workflows

Supafone Labs has two equal product pillars. Keep them mentally separate, then
combine them when the user wants the complete product.

## Pillar 1: Provider-Agnostic Framework

Use this path when the developer already has an agent running on Ultravox,
Vapi, Retell, ElevenLabs, OpenAI Realtime, Grok, Bland, LiveKit, Pipecat,
Twilio media streams, SIP, or a custom stack.

```python
import supafone_labs

brain = supafone_labs.supercharge(my_agent)
```

The framework watches call events, transcripts, tool outcomes, and call state,
then emits a silent directive only when the live agent needs help. The caller
does not hear the directive. If the watcher is disabled, out of balance, or
times out, the call continues without intervention.

## Pillar 2: Hosted Agent Factory

Use this path when the developer wants Supafone to create the agent, phone
number, voice, stages, logs, widget, and optional watcher.

This path should feel like Stripe Checkout for voice agents: one Supafone API
key first, working agent first, provider credentials only when the user chooses
advanced BYOK.

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY!,
  voiceWatcher: true, // default on — provisions agents under the Voice Watcher framework
});

const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake",
  name: "Northline intake",
  assistantName: "Maya",
  websiteUrl: "https://northline.example",
  number: { search: { areaCode: "415" } },
  labs: { enabled: true, model: "gemma" },
});
```

Python has the matching hosted-agent helpers:

```python
from supafone_labs import Supafone

supafone = Supafone(api_key="sl_live_...", voice_watcher=True)  # one key; watcher on by default

agent = supafone.labs.agents.create_inbound_with_number({
    "agentKey": "northline-intake",
    "name": "Northline intake",
    "assistantName": "Maya",
    "websiteUrl": "https://northline.example",
    "number": {"search": {"areaCode": "415"}},
    "labs": {"enabled": True, "model": "gemma"},
})
```

## Which One Should the UI Lead With?

The hosted builder should lead with the one `sl_` Labs key because that is the
lowest-friction happy path — it authenticates every surface:

1. Paste your `sl_live_...` key (as `SUPAFONE_LABS_API_KEY` / `SUPAFONE_TOKEN`).
2. Choose inbound or outbound.
3. Describe the agent.
4. Pick a voice and preview it.
5. Keep Supafone-managed providers or open advanced BYOK.
6. Create the agent and number.
7. Stream logs.
8. Export TypeScript and Python code.

The BYOK panel should be advanced. Developers should not need Twilio, Telnyx,
Plivo, SignalWire, SIP, Ultravox, Retell, Vapi, Bland, LiveKit, Pipecat,
Cartesia, Inworld, ElevenLabs, Deepgram, OpenAI, Anthropic, or xAI keys to
launch the default agent.

When BYOK is selected, group it into three lanes:

| Lane | Examples |
| --- | --- |
| Agent/provider stack | Ultravox, Retell, Vapi, Bland, LiveKit, Pipecat, GPT Realtime, Grok |
| Telephony | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks |
| TTS | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS |

## Key Routing

| Work | Key | Base URL |
| --- | --- | --- |
| Agent Factory, numbers, hosted voices | `sl_live_...` (or scoped `sf_live_...`) | `https://api.supafone.ai/api/v1/labs` |
| Oracle, TTS previews, STT, usage, logs, QA | `sl_live_...` | `https://api.labs.supafone.ai` |
| Campaigns, dialing, calls | `sl_live_...` (or account JWT) | `https://api.supafone.ai` |

Since 0.4.4, one `sl_` key authenticates on **both** APIs
([one-key auth](api-keys-and-auth.md)): both SDK constructors cross-fill every
credential lane from a lone `sl_` key, and `SUPAFONE_TOKEN=sl_live_...` is
enough for the MCP server end to end. Scoped `sf_` keys remain supported for
hosted-agent-only deployments.

## Campaigns as Code

Outbound campaigns are fully drivable from a YAML/JSON config — including
`branding:` and `intake_form:` blocks:

```yaml
slug: quote-follow-up
name: Quote follow-up
goal: book
agent: northline-outbound
branding:
  url: https://northline.example   # scanned on apply; explicit values win
intake_form:
  description: Roofing quote follow-up intake
  industry: home_services
recipients:
  - {name: Jane Doe, phone: "+15551234567", consent: yes}
```

Endpoints (product API, account JWT or `sl_` key):

```http
POST /api/v1/campaigns/config/validate
POST /api/v1/campaigns/config/apply
POST /api/v1/campaigns/config/generate
GET  /api/v1/campaigns/{campaign_id}/config
```

SDK methods: `campaigns.validate_config` / `apply_config` / `export_config` /
`generate_config` (TS: `validateConfig` / `applyConfig` / `exportConfig` /
`generateConfig`). The same flow is exposed as MCP tools
(`generate_campaign_config`, `apply_campaign_config`,
`export_campaign_config`) — see [MCP Server](mcp-server.md).

Branding and intake generation are also available standalone:

```http
POST /api/v1/agents/brand-scan                 # {url} → colors, logo, OG data
POST /api/v1/agents/generate-intake            # description → intake form
POST /api/v1/agents/{agent_id}/generate-intake # generate + apply to an agent
```

(SDK: `scan_brand` / `scanBrand`, `generate_intake_form` /
`generateIntakeForm`.)

## Export Contract

Every builder-created agent should be exportable as:

- TypeScript SDK code,
- Python SDK code,
- raw REST/curl,
- JSON configuration.

The export should contain the exact choices from the UI, including direction,
voice, number strategy, `labs.enabled`, `labs.mode`, BYOK providers, tools, and
stage preset.
