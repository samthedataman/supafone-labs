# Supafone Labs MCP Server

Local MCP server for Claude Desktop. It lets Claude create hosted Supafone voice
agents, provision numbers, and inspect Supafone Labs usage/logs through a
dependency-light Python stdio JSON-RPC server.

## What matters first: Watcher + live call loop

The MCP is not only a provisioning wrapper. It exposes the Supafone Voice
Watcher workflow so Claude can create a supervised agent, run adversarial QA
with and without Watcher intervention, place an explicitly confirmed real
call, and return a safe authenticated link to watch that exact call finish.

The shortest operator loop is:

1. `create_inbound_agent` or `create_outbound_agent` with Labs/Watcher enabled.
2. `run_watcher_qa` to measure the supervised agent against the bare agent.
3. `start_call_and_watch` with `confirmRealCall: true` and an E.164 number.
4. Open the returned `dashboard_url` for live status, transcript, recording,
   classification, and summary. The URL contains no token or secret.

The speaking agent stays on its realtime path; Watcher supervision remains
off that path and degrades to a no-op if it cannot safely intervene.

`start_call_and_watch` is carrier-neutral. It uses the calling provider already
selected for the owned Supafone agent/account: Supafone native, BYO Twilio,
**BYO Telnyx**, BYO Plivo, or BYO SIP. The MCP never receives or exposes the
provider credential; the private Supafone runtime resolves it server-side and
applies the same destination, rate-limit, and authorization controls used by
the dashboard.

**One-key setup (0.4.4+):** set `SUPAFONE_TOKEN=sl_live_...` and every tool
works — a single `sl_` Labs key authenticates on both APIs (one-key auth: the
product API introspects the key against Labs Cloud and maps it to the
app.supafone.ai account with the same email).

The explicit per-surface variables still work and take precedence when set:

- `SUPAFONE_API_KEY` for hosted agent and number provisioning on `api.supafone.ai`
- `SUPAFONE_LABS_API_KEY` for Labs Cloud usage/logs on `api.labs.supafone.ai`

## Run Locally

From this monorepo:

```bash
python3.12 /path/to/supafone-labs/mcp/supafone_mcp.py
```

The process reads newline-delimited JSON-RPC MCP messages from stdin and writes
only JSON-RPC messages to stdout.

## Claude Desktop Config

Add this to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

Restart Claude Desktop after saving the file.

## Tools

`create_inbound_agent`

Creates a hosted inbound voice agent through the Python SDK:

```json
{
  "agentKey": "northline-intake",
  "name": "Northline intake",
  "assistantName": "Maya",
  "websiteUrl": "https://northline.example",
  "labs": { "enabled": true, "model": "gemma" },
  "voice": { "provider": "cartesia", "voiceId": "db6b0ed5-d5d3-463d-ae85-518a07d3c2b4" }
}
```

`create_outbound_agent`

Creates a hosted outbound agent. Same shape as inbound, but defaults the SDK to
outbound campaign settings.

`create_inbound_agent_with_number`

Creates an inbound agent and searches/provisions a number:

```json
{
  "agentKey": "northline-intake",
  "name": "Northline intake",
  "assistantName": "Maya",
  "number": { "search": { "areaCode": "415" } },
  "labs": { "enabled": true, "mode": "supafone_managed" }
}
```

`create_outbound_agent_with_number`

Creates an outbound agent and searches/provisions a number.

`get_usage`

Reads `/v1/usage` from Supafone Labs Cloud for the configured Labs key.

`list_logs`

Reads recent `/v1/logs` rows. Use `limit` from `1` to `500`.

`tail_logs` and `poll_logs`

Poll `/v1/logs` for a short bounded stream. MCP tool calls are request/response,
so this intentionally polls instead of keeping an infinite stream open:

```json
{
  "limit": 100,
  "iterations": 10,
  "intervalSeconds": 2
}
```

### Two explicit call directions

- `get_call_modes` explains both call directions and checks grader readiness.
- `grade_existing_phone_agent` places a **real** synthetic call to any authorized E.164
  agent, independent of its AI runtime or phone carrier. It requires
  `authorized: true` and spends tester credits.
- `get_agent_grade` reads one live transcript/status snapshot.
- `wait_for_agent_grade` polls to a bounded final transcript and verdict.
- `call_from_owned_agent` makes the opposite call: one of your custom Supafone
  agents calls a human. It requires `confirmRealCall: true` and uses the same
  linked `sl_` key against the product API.
- `start_call_and_watch` is the preferred natural-language calling action. It
  starts the same guarded owned-agent call and returns `dashboard_url`, a link
  to the authenticated live call view. The link contains no token or secret;
  Supafone asks the operator to sign in when necessary and then opens the exact
  call record.
- `generate_qa_scenarios` creates adversarial cases from an agent prompt.
- `list_qa_runs` reads prior QA/Watcher results.
- `run_watcher_qa` runs the saved Builder agent with and without Watcher
  supervision. It requires `SUPAFONE_EMAIL` and `SUPAFONE_PASSWORD` because the
  saved Builder configuration is account-session scoped.
- `start_billing_checkout`, `get_billing_checkout`, and `open_billing_portal`
  return Stripe-hosted browser links for plans, credit packs, invoices, and
  payment-method management.
- `buy_phone_number` returns a clickable Checkout link for dedicated/premium
  numbers. After payment, call it again with `billingCheckoutSessionId`; the
  private API consumes the entitlement before touching the carrier.

The phone tester records `aiProvider` and `telephonyProvider` as target
metadata. PSTN is the neutral boundary, so the target can run Vapi, OpenAI
Realtime, Grok, Retell, Bland, LiveKit, Twilio, Telnyx, SIP, or another stack.

The old `test_phone_agent`, `get_phone_test`, `wait_for_phone_test`, and
`place_call` names remain callable for compatibility but are intentionally not
advertised, because their caller and target roles were ambiguous.

### Safety confirmations

MCP will not infer consent for irreversible or credit-burning operations. Real
agent calls require `confirmRealCall: true`; campaign launches require
`confirmLaunch: true`; agent/recording deletion requires `confirmDelete: true`;
and number detach/release/delete operations require `confirmRelease: true`.
`apply_campaign_config` requires `confirmLaunch: true` only when `launch: true`.

## BYOK Provider Config

Agent creation tools accept the same config style as the Python SDK. To bring
provider keys through the API, include `providerKeys`, `byok`, or provider
settings inside `labs`:

```json
{
  "agentKey": "byok-agent",
  "name": "BYOK intake",
  "labs": {
    "enabled": true,
    "mode": "byok",
    "managedInfrastructure": false,
    "stt": { "provider": "deepgram" },
    "llm": { "provider": "openai", "model": "gpt-4.1-mini" },
    "tts": { "provider": "elevenlabs" }
  },
  "providerKeys": {
    "deepgramApiKey": "dg_...",
    "elevenlabsApiKey": "sk_..."
  }
}
```

For Claude Desktop, prefer storing durable keys in the MCP `env` block rather
than typing secrets into prompts.
