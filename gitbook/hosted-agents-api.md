# 📡 Hosted Agents REST API

The hosted-agent REST API creates and manages complete Supafone agents. Use it
directly from any language or let the Python SDK, TypeScript SDK, and MCP server
wrap the same endpoints. TypeScript is optional.

```text
Base URL: https://api.supafone.ai/api/v1/labs
Auth:     Authorization: Bearer sl_live_...   # your one sl_ key (or a legacy scoped sf_live_... key)
```

Your one `sl_live_...` key works on this API via [one-key auth](api-keys-and-auth.md);
a legacy scoped `sf_live_...` key also works for hosted-agent-only setups.

Older clients may use `/api/v1/developer`, but new integrations should use
`/api/v1/labs`.

## Complete REST Endpoint Map

All routes below use the hosted base URL and the same bearer token. Reads are
account-scoped. Mutations require the account role shown by the API and cannot
cross tenants merely by supplying another `agency_id`.

| Area | Method and path | What it does | SDK surface |
| --- | --- | --- | --- |
| Discovery | `GET /capabilities` | Contract, planner modes, runtimes, telephony, presets, voices | `labs.capabilities()` |
| Discovery | `GET /presets` | List built-in industry presets | `labs.presets.list()` |
| Discovery | `GET /tools` | List built-in runtime tools | `labs.tools.list()` |
| Planning | `POST /agent-plans` | Generate or validate a reviewable 3–8 stage executable plan | `generateCallStages()` / `generate_call_stages()` / MCP `generate_call_stages` |
| Agents | `POST /agents` | Create an agent; generates a plan when stages are omitted | `labs.agents.create()` and direction helpers |
| Agents | `GET /agents` | List account agents; optional `agent_type` | `labs.agents.list()` |
| Agents | `GET /agents/{agent_key}` | Fetch one agent, runtime, and widget | `labs.agents.get()` |
| Agents | `DELETE /agents/{agent_key}` | Delete; optional `release_numbers=true` | `labs.agents.delete()` |
| Voices | `GET /voices` | Paged provider-authorized catalog with filters | `labs.voices.list()` |
| Voices | `GET /voices/preview?voice=...` | Stream an authenticated MP3 preview | REST; SDK preview helper is on Labs Cloud |
| Runtime | `GET /runtime` | Masked managed/BYOK Ultravox status | `labs.runtime.get()` |
| Runtime | `PUT /runtime` | Connect or update account-owned Ultravox runtime credentials | `labs.runtime.configure()` |
| Telephony | `GET /telephony` | Masked managed/BYOK telephony status | `labs.telephony.get()` |
| Telephony | `PUT /telephony` | Select managed mode or store Twilio/Telnyx/Plivo/SIP BYOK config | `labs.telephony.configure()` |
| Numbers | `POST /phone-numbers/search` | Search managed inventory without purchasing | `labs.phoneNumbers.search()` |
| Numbers | `GET /phone-numbers` | List account-owned numbers | `labs.phoneNumbers.list()` |
| Numbers | `POST /phone-numbers` | Explicitly provision and assign a managed number | `labs.phoneNumbers.buy()` / `buyAndAssign()` |
| Numbers | `POST /phone-numbers/{id}/assign` | Attach an owned number to an agent | `labs.phoneNumbers.assign()` |
| Numbers | `POST /phone-numbers/{id}/unassign` | Detach without releasing | `labs.phoneNumbers.unassign()` |
| Numbers | `POST /phone-numbers/{id}/release` | Release and detach | `labs.phoneNumbers.release()` |
| Numbers | `DELETE /phone-numbers/{id}` | Alias for explicit release | `labs.phoneNumbers.delete()` |
| Calls | `GET /calls` | Account call history; optional `agent_key` and `limit` | `labs.calls.list()` |
| Calls | `GET /calls/{call_id}` | One account-isolated call and its live/completed data | `labs.calls.get()` |
| Recordings | `GET /recordings` | Signed recording artifacts; optional call/agent filter | `labs.recordings.list()` |
| Recordings | `GET /recordings/{call_id}` | One signed recording artifact | `labs.recordings.get()` |
| Recordings | `DELETE /recordings/{call_id}` | Remove Supafone's reference and audit the request | `labs.recordings.delete()` |
| Transcripts | `GET /transcripts` | Transcript artifacts; optional call/agent filter | `labs.transcripts.list()` |
| Transcripts | `GET /transcripts/{call_id}` | Transcript, summary, and classification for one call | `labs.transcripts.get()` |

Recording deletion does not claim to erase a provider-retained source copy. It
returns `provider_copy_deleted: false`; configure provider retention separately.
This distinction prevents an application from showing a false compliance
confirmation.

## Discovery

```bash
curl https://api.supafone.ai/api/v1/labs/capabilities \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"

curl https://api.supafone.ai/api/v1/labs/presets \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"

curl https://api.supafone.ai/api/v1/labs/tools \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"

curl "https://api.supafone.ai/api/v1/labs/voices?provider=cartesia" \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"

curl https://api.supafone.ai/api/v1/labs/voices/capabilities \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"
```

The voice endpoint supports native-language, live-compatible-language, gender,
voice-type, model, runtime-provider, configured-provider, and text filters. See
[Dynamic Voice Catalog and Selection](voice-catalog-and-selection.md).

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

## Generate and Review a Call Plan

Give Supafone the same short brief you would give a new employee. The hosted
planner returns a complete, validated 3–8 stage plan without requiring an
Anthropic, OpenAI, or other model key in your application.

```bash
curl https://api.supafone.ai/api/v1/labs/agent-plans \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "direction": "inbound",
    "business_name": "Northline Studio",
    "industry": "professional_services",
    "description": "Answer new inquiries, understand the request, and book the right next step.",
    "tools": {"scheduling": true, "call_routing": true},
    "stage_count": 5,
    "stage_detail": "detailed"
  }'
```

The response includes `base_system_prompt`, `summary`, `call_stages`,
`generated_by`, `model`, `fallback`, and `warnings`. Each stage includes its
goal, full instructions, exit criteria, allowed tools, temperature, and valid
next stages. Review or edit that plain JSON, then pass `call_stages` to agent
creation. If you omit it, agent creation generates and installs the plan
automatically.

Only business context and enabled tool names go to the planner. Carrier,
telephony, BYOK, billing, and provider credentials do not.

## Create an Agent

```bash
curl https://api.supafone.ai/api/v1/labs/agents \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "northline-web-intake",
    "agent_type": "web",
    "style": "inbound",
    "name": "Website intake agent",
    "assistant_name": "Alex",
    "description": "Welcome visitors, understand the request, and book or route the correct next step.",
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
  "call_plan": {
    "version": "supafone_call_plan_v1",
    "generated_by": "supafone_hosted_haiku",
    "fallback": false,
    "call_stages": ["...validated executable stages..."]
  },
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

`call_plan.call_stages` is the reviewed plan installed in the agent's actual
multi-stage runtime. It is not sample copy or a UI-only preview. If hosted
generation is unavailable, Supafone returns a safe deterministic plan and
marks `fallback: true` rather than silently creating a blank agent.

## List and Fetch

```bash
curl "https://api.supafone.ai/api/v1/labs/agents?agent_type=web" \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"

curl "https://api.supafone.ai/api/v1/labs/agents/northline-web-intake" \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"
```

Delete only the agent, or explicitly release its assigned managed number too:

```bash
curl "https://api.supafone.ai/api/v1/labs/agents/northline-web-intake?release_numbers=true" \
  -X DELETE \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"
```

## Voice Catalog and Preview

`GET /voices` accepts `provider`, `search`, `language`, `cursor`, and `limit`
(1–250). Results are normalized across configured Ultravox, Cartesia,
ElevenLabs, and Inworld catalogs and include per-provider connection/errors.

```bash
curl "https://api.supafone.ai/api/v1/labs/voices?provider=cartesia&language=en-US&limit=50" \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"

curl "https://api.supafone.ai/api/v1/labs/voices/preview?voice=cartesia-sonic%3Avoice-id" \
  -H "Authorization: Bearer $SUPAFONE_TOKEN" \
  --output voice-preview.mp3
```

## TypeScript Helpers

```ts
const created = await supafone.labs.agents.create({
  agentKey: "northline-web-intake",
  agentType: "web",
  style: "inbound",
  name: "Website intake agent",
  description: "Welcome visitors, understand the request, and book or route the next step.",
  labs: { enabled: true, model: "gemma" }
});

const preview = await supafone.generateCallStages({
  direction: "inbound",
  businessName: "Northline Studio",
  description: "Answer new inquiries and book the right next step.",
  stageCount: 5,
  stageDetail: "detailed",
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
  -H "Authorization: Bearer $SUPAFONE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{ "area_code": "415", "limit": 3, "number_strategy": "default_pool" }'
```

Buy and assign must be an explicit action:

```bash
curl https://api.supafone.ai/api/v1/labs/phone-numbers \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_TOKEN" \
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
Secrets are encrypted at rest. All read responses are masked; the API never
returns stored auth tokens or provider API keys.

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
  -H "Authorization: Bearer $SUPAFONE_TOKEN" \
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

## Calls, Recordings, and Transcripts

Call artifacts are account-isolated and use the same key. Filter lists with
`agent_key`, `call_id` where supported, and `limit` (1–250).

```bash
curl "https://api.supafone.ai/api/v1/labs/calls?agent_key=northline-phone&limit=25" \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"

curl "https://api.supafone.ai/api/v1/labs/calls/CALL_ID" \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"

curl "https://api.supafone.ai/api/v1/labs/recordings?call_id=CALL_ID" \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"

curl "https://api.supafone.ai/api/v1/labs/transcripts/CALL_ID" \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"
```

Recording URLs are short-lived signed links. Transcript artifacts include the
turns, summary, and classification already attached to the call. Removing a
recording reference is an explicit staff action:

```bash
curl "https://api.supafone.ai/api/v1/labs/recordings/CALL_ID?reason=retention" \
  -X DELETE \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"
```

The response distinguishes removal from Supafone from deletion at the upstream
provider. It never reports provider deletion unless that provider confirms it.

## Errors and Safe Retries

| Status | Meaning | Developer action |
| --- | --- | --- |
| `400` | Unsupported runtime/provider or invalid operation | Show `detail`; do not retry unchanged |
| `401` | Missing, invalid, inactive, or unmapped key | Verify the key owner has a matching Supafone account |
| `403` | Valid identity without the required account role | Ask an owner/admin; never attempt another tenant ID |
| `404` | Account-scoped resource does not exist | Refresh identifiers; the API intentionally hides cross-tenant resources |
| `422` | Plan/payload validation failed | Correct the named field and resubmit |
| `429` | Plan/resource/usage limit reached | Show the returned limit or checkout path |
| `502` | A required upstream operation failed | Retry only safe, idempotent reads or use the returned recovery path |

Plan generation itself degrades to a marked deterministic fallback instead of
returning an unusable blank plan. Number purchase, number release, telephony
changes, and agent deletion are mutations—do not blindly retry them without an
idempotency or state check.


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
