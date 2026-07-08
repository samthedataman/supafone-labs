# MCP Server

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

Use hosted-agent keys for provisioning and Labs Cloud keys for logs/usage:

```bash
export SUPAFONE_API_KEY=sf_live_...
export SUPAFONE_LABS_API_KEY=sl_live_...
export SUPAFONE_API_BASE_URL=https://api.supafone.ai
export SUPAFONE_LABS_API_BASE_URL=https://api.labs.supafone.ai
```

## Claude Desktop

Add this server to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "supafone-labs": {
      "command": "python3.12",
      "args": [
        "/Users/samsavage/Downloads/voice-mono/supafone-labs/mcp/supafone_mcp.py"
      ],
      "env": {
        "SUPAFONE_API_KEY": "sf_live_...",
        "SUPAFONE_LABS_API_KEY": "sl_live_...",
        "SUPAFONE_API_BASE_URL": "https://api.supafone.ai",
        "SUPAFONE_LABS_API_BASE_URL": "https://api.labs.supafone.ai"
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
