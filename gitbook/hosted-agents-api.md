# Hosted Agents API

The hosted-agent API creates and manages Supafone-hosted agents. It is separate
from Labs Cloud.

```text
Base URL: https://api.supafone.ai/api/v1/labs
Auth:     Authorization: Bearer sf_live_...
```

Older clients may use `/api/v1/developer`, but new integrations should use
`/api/v1/labs`.

## Discovery

```bash
curl https://api.supafone.ai/api/v1/labs/capabilities \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"

curl https://api.supafone.ai/api/v1/labs/presets \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"

curl https://api.supafone.ai/api/v1/labs/tools \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"

curl "https://api.supafone.ai/api/v1/labs/voices?provider=cartesia" \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"
```

Expected capability themes:

```json
{
  "product": "Supafone Labs",
  "api_namespace": "/api/v1/labs",
  "default_agent_contract": {
    "provider": "ultravox",
    "managed_provider_accounts": true,
    "requires_developer_provider_keys": false,
    "runtime_mode": "multi_stage",
    "default_preset_key": "general_intake_receptionist",
    "labs_label": "Supafone Pro",
    "recording": true,
    "transcription": true,
    "web_widget": true,
    "default_telephony": {
      "mode": "supafone_managed",
      "provider": "supafone",
      "requires_developer_twilio_account": false
    }
  }
}
```

## Create an Agent

```bash
curl https://api.supafone.ai/api/v1/labs/agents \
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
      "firm_knowledge": true,
      "voicemail": true
    },
    "metadata": {
      "external_id": "acct_123"
    }
  }'
```

Response shape:

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
    "snippet": "<script async src=\"https://supafone.ai/widget.js\"></script>"
  }
}
```

## List and Fetch

```bash
curl "https://api.supafone.ai/api/v1/labs/agents?agent_type=web" \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"

curl "https://api.supafone.ai/api/v1/labs/agents/northline-web-intake?agent_type=web" \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"
```

## TypeScript Helpers

```ts
const created = await supafone.labs.agents.create({
  agentKey: "northline-web-intake",
  agentType: "web",
  style: "inbound",
  name: "Website intake agent",
  labs: { enabled: true, model: "gemma" }
});

const inbound = await supafone.labs.agents.createInbound({
  agentKey: "northline-phone",
  name: "Phone intake agent"
});

const outbound = await supafone.labs.agents.createOutbound({
  agentKey: "northline-sales",
  name: "Sales agent"
});
```

## Phone Number Endpoints

```http
GET  /phone-numbers
POST /phone-numbers/search
POST /phone-numbers
POST /phone-numbers/{number_id}/assign
```

Search:

```bash
curl https://api.supafone.ai/api/v1/labs/phone-numbers/search \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{ "area_code": "415", "limit": 3, "number_strategy": "default_pool" }'
```

Buy and assign must be an explicit action:

```bash
curl https://api.supafone.ai/api/v1/labs/phone-numbers \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+14155550123",
    "friendly_name": "Main intake line",
    "agent_key": "northline-phone",
    "number_strategy": "dedicated",
    "telephony": { "mode": "supafone_managed", "provider": "supafone" }
  }'
```

## Telephony

```http
GET /telephony
PUT /telephony
```

Default:

```json
{
  "mode": "supafone_managed",
  "provider": "supafone",
  "number_strategy": "default_pool"
}
```

Advanced BYOK:

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

Supported BYOK provider labels include `twilio`, `telnyx`, `plivo`, and `sip`.

