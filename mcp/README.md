# Supafone Labs MCP Server

Local MCP server for Claude Desktop. It lets Claude create hosted Supafone voice
agents, provision numbers, and inspect Supafone Labs usage/logs through a
dependency-light Python stdio JSON-RPC server.

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
  "voice": { "provider": "cartesia", "voiceId": "sonic-warm" }
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

### Universal tester and Watcher QA

- `get_tester_capabilities` checks whether the managed phone grader is ready.
- `test_phone_agent` places a **real** synthetic call to any authorized E.164
  agent, independent of its AI runtime or phone carrier. It requires
  `authorized: true` and spends tester credits.
- `get_phone_test` reads one live transcript/status snapshot.
- `wait_for_phone_test` polls to a bounded final transcript and verdict.
- `generate_qa_scenarios` creates adversarial cases from an agent prompt.
- `list_qa_runs` reads prior QA/Watcher results.
- `run_watcher_qa` runs the saved Builder agent with and without Watcher
  supervision. It requires `SUPAFONE_EMAIL` and `SUPAFONE_PASSWORD` because the
  saved Builder configuration is account-session scoped.

The phone tester records `aiProvider` and `telephonyProvider` as target
metadata. PSTN is the neutral boundary, so the target can run Vapi, OpenAI
Realtime, Grok, Retell, Bland, LiveKit, Twilio, Telnyx, SIP, or another stack.

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
