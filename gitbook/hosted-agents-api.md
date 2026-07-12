# 📡 Hosted Agents API

The hosted-agent API creates and manages Supafone-hosted agents. It is separate
from Labs Cloud.

```text
Base URL: https://api.supafone.ai/api/v1/labs
Auth:     Authorization: Bearer sl_live_...   # your one sl_ key (or a legacy scoped sf_live_... key)
```

Your one `sl_live_...` key works on this API via [one-key auth](api-keys-and-auth.md);
a legacy scoped `sf_live_...` key also works for hosted-agent-only setups.

Older clients may use `/api/v1/developer`, but new integrations should use
`/api/v1/labs`.

## Discovery

```bash
curl https://api.supafone.ai/api/v1/labs/capabilities \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"

curl https://api.supafone.ai/api/v1/labs/presets \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"

curl https://api.supafone.ai/api/v1/labs/tools \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"

curl "https://api.supafone.ai/api/v1/labs/voices?provider=cartesia" \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"
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
    "byok": {
      "ultravox": { "api_key": "string", "base_url": "string (optional)" }
    },
    "default_telephony": {
      "mode": "supafone_managed",
      "provider": "supafone",
      "requires_developer_twilio_account": false
    }
  },
  "runtimes": {
    "available": ["ultravox"],
    "managed": "ultravox",
    "byok": ["ultravox"],
    "coming_soon": ["vapi", "retell", "bland", "livekit", "pipecat"]
  }
}
```

The `runtimes` block is honest about what runs today: Ultravox is available
both **managed** (Supafone's platform key) and **BYOK** (your own key); Vapi,
Retell, Bland, LiveKit, and Pipecat are still coming soon and their agent
runtimes return **400 "coming soon"**.

## Create an Agent

```bash
curl https://api.supafone.ai/api/v1/labs/agents \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY" \
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

To run the agent on your **own** Ultravox account, add a `byok.ultravox` block
to the create body — `{"api_key": "uvx_...", "base_url": "https://api.ultravox.ai/api"}`
(`base_url` optional; a `byok.credentials` object is also accepted as the key
holder). The key is stored encrypted on your account, never in the agent doc,
and `runtime_mode` becomes `"byok"`. See [Runtime](#runtime-managed-vs-byok-ultravox)
below, or connect it standalone with `PUT /runtime`.

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
    "provider": "ultravox",
    "managed": true,
    "key_source": "platform",
    "status": "ready",
    "model": "...",
    "direction": "inbound",
    "telephony": { "mode": "supafone_managed", "provider": "supafone" }
  },
  "widget": {
    "widget_key": "sf_...",
    "snippet": "<script async src=\"https://supafone.ai/widget.js\"></script>"
  }
}
```

In the `runtime` block, `managed` is `false` and `key_source` is `"byok"` when
the agent runs on your own Ultravox key; `status` is `"simulated"` when neither a
platform nor a BYOK runtime key is connected.

## List and Fetch

```bash
curl "https://api.supafone.ai/api/v1/labs/agents?agent_type=web" \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"

curl "https://api.supafone.ai/api/v1/labs/agents/northline-web-intake?agent_type=web" \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"
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
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{ "area_code": "415", "limit": 3, "number_strategy": "default_pool" }'
```

Buy and assign must be an explicit action:

```bash
curl https://api.supafone.ai/api/v1/labs/phone-numbers \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY" \
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

## Runtime (managed vs BYOK Ultravox)

The agent runtime runs on Ultravox. By default it uses Supafone's managed
platform key (managed billing). Connect your **own** Ultravox account to place
and monitor agents on your key; `runtime_mode` becomes `"byok"`.

```http
GET /runtime
PUT /runtime
```

Connect or update your key:

```bash
curl https://api.supafone.ai/api/v1/labs/runtime \
  -X PUT \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ultravox",
    "credentials": { "api_key": "uvx_...", "base_url": "https://api.ultravox.ai/api" }
  }'
```

`base_url` is optional. A blank `api_key` keeps the stored key, so you can
re-save other fields. A non-`ultravox` provider returns **400 "coming soon"**.
Both `GET` and `PUT` return the same status shape:

```json
{
  "account_id": "...",
  "provider": "ultravox",
  "managed": false,
  "byok_connected": true,
  "base_url": "https://api.ultravox.ai/api",
  "updated_at": "2026-07-11T00:00:00Z"
}
```

You can also connect the key at agent create via `byok.ultravox`. Non-Ultravox
agent runtimes (Vapi, Retell, Bland, LiveKit, Pipecat) still return
**400 "coming soon"**.


## Brand Scan and Intake Generation

The product API (`https://api.supafone.ai`, account JWT or `sl_` key via
one-key auth) exposes the onboarding brand/intake machinery directly:

```http
POST /api/v1/agents/brand-scan                 # {"url": "..."} → business name, colors, logo, favicon, OG metadata, images, key pages
POST /api/v1/agents/generate-intake            # {"description": "...", "industry": "..."} → generated intake form config
POST /api/v1/agents/{agent_id}/generate-intake # generate and apply to that agent
POST /api/v1/agents/{agent_id}/intake/reset    # reset an agent's intake form
```

SDK: `supafone.scan_brand(url)` / `supafone.scanBrand(url)` and
`supafone.generate_intake_form(...)` / `supafone.generateIntakeForm(...)`.
The same capabilities drive the campaign YAML `branding:` and `intake_form:`
blocks — see [Developer Workflows](developer-workflows.md).
