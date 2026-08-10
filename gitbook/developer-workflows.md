# 🧑‍💻 Developer Workflows

Supafone Labs has one defining framework and one secondary delivery path. Lead
with the model-agnostic supervisor; use Agent Factory when the user also wants
Supafone to provision the complete hosted product.

## Primary: Model-Agnostic Voice Watcher

Use this path when the developer already has an agent running on Ultravox,
Vapi, Retell, ElevenLabs, OpenAI Realtime, Grok, Bland, LiveKit, Pipecat,
Twilio media streams, SIP, or a custom stack.

```python
import supafone_labs

brain = supafone_labs.supercharge(my_agent)
```

The framework watches empathy and operational patterns across turns—intent,
urgency, emotion, language, trust, workflow progress, tool outcomes, and call
state—then emits a silent directive only when the live agent needs help. The
caller does not hear the directive. If the Watcher is disabled, out of balance,
or times out, the call continues without intervention.

## Secondary: Hosted Agent Factory

Use this path when the developer wants Supafone to create the agent, phone
number, voice, stages, logs, widget, and optional watcher.

This path should feel like Stripe Checkout for voice agents: one Supafone API
key first, working agent first, provider credentials only when the user chooses
advanced BYOK.

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_TOKEN!,
  voiceWatcher: true, // default on — provisions agents under the Voice Watcher framework
});

const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake",
  name: "Northline intake",
  assistantName: "Maya",
  description: "Answer new inquiries, understand the request, and book the right next step.",
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
    "description": "Answer new inquiries, understand the request, and book the right next step.",
    "websiteUrl": "https://northline.example",
    "number": {"search": {"areaCode": "415"}},
    "labs": {"enabled": True, "model": "gemma"},
})
```

## What This Removes From Daily Development

### One voice catalog instead of provider-specific integrations

The Python and TypeScript SDKs expose one normalized catalog across Cartesia,
Inworld, ElevenLabs, and Ultravox. Developers can search by language, provider,
model, gender, accent, voice type, configured status, or free text without
maintaining separate provider response types or voice-ID spreadsheets.

```ts
const matches = await supafone.labs.voices.recommend({
  description: "warm Puerto Rican Spanish patient-support voice",
  language: "es-PR",
  configuredOnly: true,
});
```

The catalog separates three facts that providers commonly blur together:

- the language native to the individual speaker;
- the languages supported by the selected TTS model;
- the intersection the managed Ultravox runtime can actually use.

This makes an incompatible selection a provisioning error instead of a failed
customer call. Direct voice selection remains available when the developer
already knows the exact provider voice ID.

### Configure a fixed language once

Agent Factory accepts one preferred BCP-47 language and uses it as the default
voice-compatibility filter:

```ts
const agent = await supafone.labs.agents.createInbound({
  name: "Spanish intake",
  preferredLanguage: "es-MX",
  greeting: "Gracias por llamar. ¿Cómo puedo ayudarle?",
  voicePreference: {
    description: "warm female patient-support voice",
    configuredOnly: true,
  },
});
```

```python
agent = supafone.labs.agents.create_inbound({
    "name": "Spanish intake",
    "preferred_language": "es-MX",
    "greeting": "Gracias por llamar. ¿Cómo puedo ayudarle?",
    "voice_preference": {
        "description": "warm female patient-support voice",
        "configured_only": True,
    },
})
```

The locale is applied to the initial PSTN or WebRTC call and every later call
stage. It is fixed for the full call. This option does **not** install a
language-switch tool, detect accents, or change voices mid-call.

The fixed-language marker is additive and Agent-Factory-specific. Existing
agents and agents made in a manual builder keep their historical payloads when
the option is omitted.

### Make the supervisor output an application contract

SecondMind can return a typed, inspectable decision instead of an unstructured
coaching sentence:

```ts
const directive = await supafone.whisperStructured(transcript, {
  directiveContract: {
    confidenceThreshold: 0.8,
    languageMode: "caller",
    empathyDirective: {
      enabled: true,
      instructions: "Use one short acknowledgement; do not over-apologize.",
    },
    tacticalDirective: {
      enabled: true,
      instructions: "Choose one next operational action.",
    },
    operatorGuardrails: [
      "Do not claim a booking, transfer, or delivery until its tool confirms it.",
    ],
  },
});
```

Developers can enable or disable fields, constrain directive kinds, set a
confidence gate, add standing guardrails, and transform or suppress the final
directive before delivery. Facts, empathy, tactics, and policy stay separate,
which makes the supervisor output easier to log, test, audit, and replay.

See [Programmable SecondMind Directives](secondmind-directive-contract.md).

### Reuse the same integration across clients

The same agent configuration works from Python services, TypeScript servers,
React applications, scripts, and exported campaign configurations. Provider
identity stays in normalized selection objects instead of leaking throughout
business code. A consulting team can therefore change the industry prompt,
tools, voice preference, number, and branding without rebuilding telephony,
voice discovery, supervision, or validation for every client.

### Debug failures before and after a call

- Provisioning responses contain the selected provider, voice ID, model,
  matching score, and reasons.
- Structured SecondMind output records facts, directives, language, kind,
  confidence, and guardrails independently.
- Invalid language/model/runtime combinations fail before dialing.
- Watcher timeouts or suppressed low-confidence directives leave the live call
  unchanged.

These behaviors reduce provider-specific glue code while preserving explicit
failure boundaries. See [Dynamic Voice Catalog and Selection](voice-catalog-and-selection.md),
[Agent Factory](agent-factory.md), and [Self-Healing Watcher](self-healing-watcher.md).

## Which One Should the UI Lead With?

The product story should lead with Voice Watcher. Inside the hosted builder,
the task flow should then lead with the one `sl_` Labs key because that is the
lowest-friction provisioning path—it authenticates every surface:

1. Paste your `sl_live_...` key (as `SUPAFONE_LABS_API_KEY` / `SUPAFONE_TOKEN`).
2. Choose inbound or outbound.
3. Describe the agent.
4. Review the generated prompts and 3–8 stage plan when approval matters.
5. Pick a voice and preview it.
6. Keep Supafone-managed providers or open advanced BYOK.
7. Create the agent and number.
8. Stream logs.
9. Export REST, TypeScript, Python, MCP, or JSON.

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
- MCP tool calls,
- JSON configuration.

The export should contain the exact choices from the UI, including direction,
voice, number strategy, `labs.enabled`, `labs.mode`, BYOK providers, tools, and
stage preset, and the exact generated or edited call plan.
