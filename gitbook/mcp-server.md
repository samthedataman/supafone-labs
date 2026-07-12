# 🔗 MCP Server

Supafone Labs ships a local MCP server for Claude Desktop under:

```text
supafone-labs/mcp/supafone_mcp.py
```

It is a dependency-light Python stdio JSON-RPC server. Claude can use it to
create hosted agents, provision numbers, check usage, and poll Labs logs.

Use this when you want Claude Desktop to run agent-team experiments: one tool
call can create an inbound receptionist, another can create an outbound sales
agent, and a third can tail logs while the team evaluates different provider
configurations.

## Environment

**One-key setup (recommended, 0.4.4+):** a single `sl_` Labs key authenticates
everything — the Labs Cloud tools *and* the campaign/calling tools on the main
product API (via [one-key auth](api-keys-and-auth.md)). Set one env var:

```bash
export SUPAFONE_TOKEN=sl_live_...   # one key: labs + campaigns + calls
```

The only requirement is that an app.supafone.ai account exists with the same
email that owns the key.

The older, explicit per-surface variables still work and take precedence when
set:

```bash
export SUPAFONE_API_KEY=sl_live_...       # your one sl_ key (or a scoped sf_ hosted-agent key)
export SUPAFONE_LABS_API_KEY=sl_live_...  # Labs Cloud logs/usage
export SUPAFONE_API_BASE_URL=https://api.supafone.ai
export SUPAFONE_LABS_API_BASE_URL=https://api.labs.supafone.ai
```

For the campaign and calling tools, `SUPAFONE_TOKEN` may also hold an
app.supafone.ai JWT, or the server can log in for you (and transparently
re-login when the token expires):

```bash
export SUPAFONE_TOKEN=eyJ...            # an app.supafone.ai JWT, or:
export SUPAFONE_EMAIL=you@company.com
export SUPAFONE_PASSWORD=...
```

## Claude Desktop

Add this server to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "supafone-labs": {
      "command": "python3.12",
      "args": [
        "/path/to/supafone-labs/mcp/supafone_mcp.py"
      ],
      "env": {
        "SUPAFONE_TOKEN": "sl_live_..."
      }
    }
  }
}
```

Restart Claude Desktop after saving the config.

## Tools

| Tool | Purpose |
| --- | --- |
| `create_inbound_agent` | Create an inbound hosted voice agent through the Python SDK. |
| `create_outbound_agent` | Create an outbound hosted voice agent through the Python SDK. |
| `create_inbound_agent_with_number` | Create an inbound agent and provision or assign a number. |
| `create_outbound_agent_with_number` | Create an outbound agent and provision or assign a number. |
| `get_usage` | Read Labs Cloud usage and caps from `/v1/usage`. |
| `list_logs` | Read recent Labs Cloud logs from `/v1/logs`. |
| `tail_logs` | Poll Labs Cloud logs for a bounded live-looking stream. |
| `poll_logs` | Alias for `tail_logs`. |

### Campaigns & calls (main-app account login)

| Tool | Purpose |
| --- | --- |
| `place_call` | **Places a real outbound phone call**: dials a number and bridges your voice agent onto the line. |
| `list_voice_agents` | List the account's voice agents to pick an `agentId` for calls and campaigns. |
| `list_campaigns` | List outbound campaigns with live stats. |
| `create_campaign` | Create a draft campaign (`goal`: book / qualify / follow_up / reengage). |
| `get_campaign` | Fetch one campaign's config, settings, cadence, and stats. |
| `update_campaign` | Update name/goal/agent/email copy/cadence/settings (settings merge server-side). |
| `add_campaign_recipients` | Add consented leads (`{name, phone, email, outreach_consent:"yes"}`). |
| `list_campaign_recipients` | List recipients with their cadence state. |
| `launch_campaign` | **Starts real calls/emails** on the cadence immediately. |
| `pause_campaign` | Pause an active campaign. |
| `list_campaign_presets` | Built-in playbooks plus the account's saved custom presets. |
| `apply_campaign_preset` | Materialize a preset (goal, questions, scripts, signing doc) in one write. |
| `create_sign_link` | Mint a recipient's tracked tap-to-sign page (inherits the campaign's signing PDF). |
| `monitor_campaign` | Watch a campaign live: in-flight calls + recent calls, each with a portal listen link. |
| `get_call` | One call's record — poll it while in progress to follow the live transcript. |

### Campaigns as code (YAML config)

| Tool | Purpose |
| --- | --- |
| `generate_campaign_config` | Draft a full campaign YAML from a plain-English description. |
| `apply_campaign_config` | Validate, then apply a YAML/JSON campaign config (inline or `filePath`) — creates or updates the campaign, recipients, branding, and intake form in one write. |
| `export_campaign_config` | Round-trip an existing campaign back out as YAML. |

Campaign configs support `branding:` (`{url}` to scan on apply, and/or explicit
colors/logo/favicon — explicit wins) and `intake_form:`
(`{description[, industry]}` to LLM-generate on apply, or an explicit
`config:` block) alongside goal, agent, cadence, recipients, and outbound
script keys.

### Branding & intake generation

| Tool | Purpose |
| --- | --- |
| `scan_brand` | Scan a website for its branding: business name, colors, logo, favicon, OG metadata, images, key pages — the same detection that styles agents during onboarding, as plain data. |
| `generate_intake_form` | LLM-generate an intake form from a description (optionally per industry), standalone or applied straight to an agent. |

### E-sign documents

| Tool | Purpose |
| --- | --- |
| `upload_signing_document` | Upload a PDF (e.g. a retainer) as a campaign's signing document. |
| `detect_signature_fields` | Auto-detect signature/date/initial coordinates on the uploaded PDF. |
| `set_signature_fields` | Set or adjust the placed signature fields explicitly. |

Together these make the whole signature-chase drivable from prose: upload the
retainer, apply the detected coordinates, add leads, launch, then
`create_sign_link` per recipient.

## The coolest things to ask for

These all work in plain English in Claude Desktop / Claude Code once the
server is configured — Claude picks the tools, you get links back.

### "Launch a campaign from this list"

> *"Create a win-back campaign using my Northline agent. Add these leads —
> Jane Doe +1 555 123 4567, Marcus Reid +1 555 987 6543, both consented —
> apply the win-back playbook, and launch it."*

Claude chains `list_voice_agents` → `create_campaign` → `apply_campaign_preset`
→ `add_campaign_recipients` → `launch_campaign`. Real calls start dialing on
the cadence within seconds.

### "Call me so I can hear my agent"

> *"Place a call from my sales agent to my cell, +1 555 000 1111 — I want to
> hear how it sounds."*

`place_call` rings your phone and bridges the voice agent onto the line. The
fastest possible demo of your own agent.

### "Who's on the phone right now? Let me listen"

> *"Which campaign calls are happening right now? Give me links to listen in."*

`monitor_campaign` returns the live funnel and every in-flight call with a
portal link — open one and watch the transcript grow as the conversation
happens. The campaign-level link opens the developer portal
(`app.supafone.ai/app/developer`) with all of it live on one page.

### "Follow that call and tell me how it ends"

> *"Keep an eye on the call with Jane and tell me whether she books."*

Claude polls `get_call` — each poll returns the transcript so far — and
narrates the conversation as it unfolds, then reports the outcome and
classification when the call completes.

### "Chase signatures on our retainer"

> *"Start a signature-chase for the Henderson matter: apply my
> 'Retainer signature chase' preset and send Jane her signing link."*

A custom preset carries your questions, scripts, email copy, AND the uploaded
retainer PDF with placed signature fields. `apply_campaign_preset` +
`create_sign_link` put a tracked tap-to-sign page in Jane's hands; when she
signs, the stamped PDF lands on her lead row and in your inbox.

### "Spin up an agent AND put it to work"

> *"Create an outbound agent for Northline Roofing with a 415 number, then
> build a quote-follow-up campaign with it and add yesterday's quotes."*

Hosted-agent provisioning (`create_outbound_agent_with_number`) and the
campaign tools compose — one conversation goes from nothing to a staffed,
dialing campaign.

### "Build the whole campaign from my website"

> *"Scan northline.example for our branding, draft a quote-follow-up campaign
> config with an intake form for roofing leads, show me the YAML, then apply
> it."*

`scan_brand` → `generate_campaign_config` → `apply_campaign_config`. The
applied campaign carries your real colors and logo, an LLM-generated intake
form, cadence, and scripts — and `export_campaign_config` round-trips it back
to YAML for version control.

### "Tune the script mid-flight"

> *"Pause the campaign, make the opening warmer — mention we spoke at the
> home show — and relaunch."*

`pause_campaign` → `update_campaign` (settings.outbound_prompts) →
`launch_campaign`. The next dial uses the new script; the builder UI shows
the same change instantly.

## Example Agent

```json
{
  "agentKey": "northline-intake",
  "name": "Northline intake",
  "assistantName": "Maya",
  "websiteUrl": "https://northline.example",
  "number": { "search": { "areaCode": "415" } },
  "labs": {
    "enabled": true,
    "mode": "supafone_managed",
    "model": "gemma"
  },
  "voice": {
    "provider": "cartesia",
    "voiceId": "sonic-warm"
  }
}
```

For BYOK, keep the three credential lanes separate:

| Lane | MCP/config fields |
| --- | --- |
| Agent/provider stack | `byok.agentProvider`, `providerKeys.ultravoxApiKey`, `providerKeys.retellApiKey`, `providerKeys.vapiApiKey` |
| Telephony | `byok.telephony`, `telephony.credentials`, `telephony.customSip` |
| TTS | `byok.tts`, `providerKeys.cartesiaApiKey`, `providerKeys.elevenlabsApiKey`, `providerKeys.inworldApiKey` |

For durable credentials, prefer the MCP env block or account credential store
instead of prompt text.

MCP also exposes lifecycle and artifact tools:

- `delete_agent`
- `generate_call_stages`
- `list_voices` / `preview_voice`
- `list_phone_numbers`
- `search_phone_numbers`
- `unassign_phone_number`
- `return_phone_number_to_pool`
- `delete_phone_number`
- `list_calls`
- `list_recordings`
- `delete_recording`
- `list_transcripts`
- `list_logs` / `tail_logs`

## Log Streaming Note

MCP tool calls are request/response. The local MCP server therefore exposes
`tail_logs` and `poll_logs` as bounded polling tools. The browser and SDKs can
use the true SSE stream documented in [Log Streaming](log-streaming.md).
