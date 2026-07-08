# Hosted Agents API

Use the Supafone Labs API when you want Supafone to host the voice/web/campaign
agent for you. This is a convenience layer over the Supafone runtime: Ultravox
calls, multistage state, managed voice provider accounts, tools, transcripts,
recordings, web widget sync, and Supafone Pro stay attached.

This is the agent-building framework path. Developers bring a Supafone key and
the business goal; Supafone Labs gives them voice choices, built-in stage
presets, routing and workflow tools, call artifacts, and live call coaching
without forcing them to wire provider accounts by hand.

The public namespace is:

```text
https://api.supafone.ai/api/v1/labs
```

The compatibility namespace `/api/v1/developer` exists for older clients, but
new code should use `/api/v1/labs`.

The recommended TypeScript package is `supafone-labs`:

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_API_KEY!,
});

const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake",
  name: "Northline intake",
  assistantName: "Maya",
  websiteUrl: "https://northline.example",
  number: { search: { areaCode: "415" } },
  labs: { enabled: true, model: "gemma" },
});

console.log(agent.agent.agent_key, agent.number?.number.phone_number);
```

## Auth

Hosted-agent API calls use a Supafone hosted-agent API key. It starts with
`sf_live_...`.

```bash
export SUPAFONE_API_KEY=sf_live_...
export SUPAFONE_API_BASE_URL=https://api.supafone.ai
```

Pass the key as a bearer token:

```bash
curl "$SUPAFONE_API_BASE_URL/api/v1/labs/capabilities" \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"
```

The same key also works in `x-supafone-key` or `x-supafone-api-key`.

Do not confuse this with the Labs cloud key (`SUPAFONE_LABS_API_KEY=sl_live_...`)
used for oracle/TTS/STT calls on `https://api.labs.supafone.ai`. If you use the
TypeScript SDK for both products, pass the hosted key as `supafoneApiKey`.

## API keys

Creating, listing, and revoking API keys is an account-admin action. It uses the
normal Supafone app user session/JWT, not the Labs key itself:

```http
POST   /api/v1/labs/api-keys
GET    /api/v1/labs/api-keys?agency_id=...
DELETE /api/v1/labs/api-keys/{key_id}?agency_id=...
```

Create body:

```json
{
  "agency_id": "00000000-0000-0000-0000-000000000000",
  "name": "Production key",
  "scopes": [
    "agents:write",
    "agents:read",
    "voices:read",
    "calls:write",
    "numbers:read",
    "numbers:write",
    "telephony:read",
    "telephony:write"
  ]
}
```

Create response returns the raw key once:

```json
{
  "api_key": "sf_live_...",
  "key": {
    "id": "key-id",
    "name": "Production key",
    "agency_id": "00000000-0000-0000-0000-000000000000",
    "key_prefix": "sf_live_xxx...abcd",
    "scopes": ["agents:write", "agents:read", "voices:read", "calls:write", "numbers:read", "numbers:write", "telephony:read", "telephony:write"],
    "last_used_at": null,
    "revoked_at": null,
    "created_at": "2026-07-06T00:00:00Z",
    "updated_at": "2026-07-06T00:00:00Z"
  }
}
```

List and revoke responses never include the raw key or hash.

## Discovery

Start with capabilities so your app can check what the key can do:

```bash
curl "$SUPAFONE_API_BASE_URL/api/v1/labs/capabilities" \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"
```

Important response fields:

```json
{
  "product": "Supafone Labs",
  "api_namespace": "/api/v1/labs",
  "default_agent_contract": {
    "provider": "ultravox",
    "ultravox_superclass": true,
    "managed_provider_accounts": true,
    "requires_developer_provider_keys": false,
    "runtime_mode": "multi_stage",
    "default_preset_key": "general_intake_receptionist",
    "labs_label": "Supafone Pro",
    "default_watcher_model": "gemma",
    "recording": true,
    "transcription": true,
    "web_widget": true,
    "agent_styles": ["inbound", "outbound"],
    "default_telephony": {
      "mode": "supafone_managed",
      "provider": "supafone",
      "number_buying": "supafone_master_twilio",
      "requires_developer_twilio_account": false
    }
  }
}
```

List presets:

```bash
curl "$SUPAFONE_API_BASE_URL/api/v1/labs/presets" \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"
```

List built-in tools:

```bash
curl "$SUPAFONE_API_BASE_URL/api/v1/labs/tools" \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"
```

List Supafone-managed voices:

```bash
curl "$SUPAFONE_API_BASE_URL/api/v1/labs/voices?provider=cartesia" \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"
```

Voice responses include:

```json
{
  "voices": [],
  "total": 0,
  "providers": [
    {
      "key": "cartesia",
      "name": "Cartesia through Ultravox",
      "managed_by": "supafone",
      "requires_developer_provider_key": false
    }
  ],
  "provider_accounts": {
    "mode": "supafone_managed",
    "requires_developer_provider_keys": false,
    "optional_provider_override_enabled": false
  }
}
```

## Create an agent

```bash
curl "$SUPAFONE_API_BASE_URL/api/v1/labs/agents" \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "northline-web-intake",
    "agent_type": "web",
    "style": "inbound",
    "name": "Website intake agent",
    "assistant_name": "Alex",
    "business_name": "Northline Studio",
    "industry": "professional_services",
    "website_url": "https://example.com",
    "preset_key": "general_intake_receptionist",
    "runtime_mode": "multi_stage",
    "voice": {
      "provider": "cartesia",
      "voice_id": "Jacqueline"
    },
    "labs": {
      "enabled": true,
      "model": "gemma"
    },
    "tools": {
      "call_routing": true,
      "scheduling": true,
      "sms": true,
      "email": true,
      "intake_forms": true,
      "firm_knowledge": true,
      "voicemail": true
    },
    "metadata": {
      "external_id": "acct_123"
    }
  }'
```

The SDK accepts camelCase names such as `agentKey`, `assistantName`,
`websiteUrl`, `runtimeMode`, `callRouting`, and `firmKnowledge`; raw HTTP accepts
the snake_case names shown above.

Create response:

```json
{
  "success": true,
  "agent": {
    "agent_key": "northline-web-intake",
    "agent_type": "web",
    "display_name": "Website intake agent",
    "runtime_mode": "multi_stage",
    "preset_key": "general_intake_receptionist"
  },
  "runtime": {
    "provider_accounts": {
      "mode": "supafone_managed",
      "requires_developer_provider_keys": false
    }
  },
  "widget": {
    "widget_key": "sf_...",
    "snippet": "<script async src=\"https://supafone.ai/widget.js\" ...></script>"
  }
}
```

## List and fetch agents

List agents:

```bash
curl "$SUPAFONE_API_BASE_URL/api/v1/labs/agents?agent_type=web" \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"
```

Fetch one agent:

```bash
curl "$SUPAFONE_API_BASE_URL/api/v1/labs/agents/northline-web-intake?agent_type=web" \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"
```

The API key is scoped to one Supafone account. Passing another `agency_id`
returns `403`.

## Phone numbers and telephony

The default path is Supafone-managed. Developers do **not** need a Twilio
account to search, buy, assign, or route a number. Supafone buys through its
managed telephony account, configures webhooks, and keeps the line synced to the
same account, dashboard, recordings, transcripts, and call artifacts.

Search inventory:

```bash
curl "$SUPAFONE_API_BASE_URL/api/v1/labs/phone-numbers/search" \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{ "area_code": "787", "limit": 3 }'
```

Buy and assign a Supafone-managed number:

```bash
curl "$SUPAFONE_API_BASE_URL/api/v1/labs/phone-numbers" \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+17875550123",
    "friendly_name": "Main intake line",
    "agent_key": "northline-web-intake",
    "style": "inbound",
    "preset_key": "general_intake_receptionist",
    "telephony": { "mode": "supafone_managed", "provider": "supafone" }
  }'
```

Attach an already-owned Supafone number to another agent:

```http
POST /api/v1/labs/phone-numbers/{number_id}/assign
```

List owned numbers:

```http
GET /api/v1/labs/phone-numbers
```

Read or configure telephony:

```http
GET /api/v1/labs/telephony
PUT /api/v1/labs/telephony
```

BYOK is the advanced path for developers who already own provider accounts. It
is not required for the default Supafone-managed flow. Keep BYOK split into
three lanes:

| Lane | Examples |
| --- | --- |
| Agent/provider stack | Ultravox, Retell, Vapi, Bland, LiveKit, Pipecat, GPT Realtime, Grok |
| Telephony | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks |
| TTS | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS |

BYOK telephony example:

```json
{
  "mode": "byok",
  "provider": "twilio",
  "credentials": {
    "account_sid": "AC...",
    "auth_token": "...",
    "from_number": "+14155550123"
  }
}
```

Supported BYOK telephony provider labels include `twilio`, `telnyx`, `plivo`,
`signalwire`, `sip`, and custom provider labels enabled for the account.
Supafone still keeps the agent framework, stages, tools, transcripts,
recordings, account sync, and Supafone Pro watcher attached.

## Supafone Pro

Turn on the watcher with either field:

```json
{
  "labs": { "enabled": true, "model": "gemma" }
}
```

or:

```json
{
  "voice_watcher": true,
  "voice_watcher_model": "gemma"
}
```

The product label is **Supafone Pro**. It is the same Labs watcher/call-coach
capability attached to the hosted agent.

## Smoke test

Run the production smoke script before handing an API key to a developer:

```bash
cd supafone-labs
SUPAFONE_API_KEY=sf_live_... \
SUPAFONE_API_BASE_URL=https://api.supafone.ai \
npx tsx examples/smoke-hosted-agent.ts
```

The script verifies capabilities, presets, voices, agent creation, fetch-by-key,
Supafone-managed runtime, no required developer provider keys, and a returned
web widget snippet.

## What still happens in the Supafone app

Some account operations belong in the main Supafone app/API:

- creating the initial account and user session,
- creating and revoking Labs API keys,
- billing and subscription management,
- call history, recordings, transcripts, leads, and usage views.

Number purchase and assignment now exist in the hosted-agent API as a developer
surface too; the Supafone app remains the visual setup and billing console.
The hosted-agent API is intentionally focused on creating and managing agents
from code while keeping all artifacts synced to the same Supafone account.
