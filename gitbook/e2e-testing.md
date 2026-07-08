# E2E Testing

Use focused tests for each surface: SDK, Labs Cloud, hosted-agent API, builder,
and live provider paths.

## Hosted-Agent Smoke Test

```bash
cd supafone-labs
SUPAFONE_API_KEY=sf_live_... \
SUPAFONE_API_BASE_URL=https://api.supafone.ai \
npx tsx examples/smoke-hosted-agent.ts
```

The script verifies:

- `/api/v1/labs/capabilities` returns the Labs namespace,
- `general_intake_receptionist` preset exists,
- Supafone-managed voices are discoverable,
- a web intake agent can be created,
- the agent can be fetched by key,
- `provider_accounts.mode` is `supafone_managed`,
- developer provider keys are not required,
- a widget snippet is returned.

## Python SDK Tests

```bash
cd supafone-labs
python3.12 -m pytest tests -q -m "not live"
python3.12 -m ruff check src
```

Live provider tests should be opt-in and require provider keys and network
access.

## TypeScript SDK Build

```bash
cd supafone-labs/sdk-ts
npm run build
npm --cache /tmp/supafone-npm-cache pack --dry-run
```

## Labs Cloud API Smoke

```bash
curl https://api.labs.supafone.ai/healthz

curl https://api.labs.supafone.ai/v1/pricing

curl https://api.labs.supafone.ai/v1/billing/balance \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"
```

## Builder and QA E2E

```ts
await supafone.login(process.env.SM_EMAIL!, process.env.SM_PASSWORD!);

await supafone.builder.saveConfig({
  agent_prompt: "You are a careful intake agent. Never quote fees.",
  agent_label: "intake",
  framework: "ultravox",
  llm: { provider: "hosted" }
});

const turn = await supafone.builder.chat("e2e-1", [
  { role: "agent", text: "How can I help?" },
  { role: "caller", text: "What do you charge?" }
]);

const qa = await supafone.qa.run({ turns: 2 });
```

## Logs Stream E2E

The API exposes both snapshot logs and SSE streaming. Run the focused tests:

```bash
cd supafone-labs
python3.12 -m pytest tests/test_cloud_logs_stream.py tests/test_hosted_agents_client.py -q
```

Manual stream check:

```bash
curl -N "https://api.labs.supafone.ai/v1/logs/stream?limit=20&poll_ms=1000&snapshot=true" \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"
```

The stream should emit `event: log` rows with the same shape as `/v1/logs`.

## Voice Catalog and Preview E2E

```bash
curl https://api.labs.supafone.ai/v1/voices

curl https://api.labs.supafone.ai/v1/tts \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY" \
  -H "Content-Type: application/json" \
  --output /tmp/supafone-preview.wav \
  -d '{"voice":"cartesia:sonic-warm","text":"Hi, this is a Supafone voice preview."}'
```

The hosted-agent voice catalog should also work with the hosted-agent key:

```bash
curl "https://api.supafone.ai/api/v1/labs/voices?provider=cartesia" \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"
```

## Agent Factory E2E Matrix

| Test | Expected result |
| --- | --- |
| `createInboundWithNumber()` default pool | Agent plus assigned shared/pool number |
| `createOutboundWithNumber()` default pool | Outbound/campaign agent plus assigned caller ID |
| `labs.enabled: false` | Agent created without watcher sidecar |
| `labs.enabled: true`, managed | Watcher config uses Supafone-managed infrastructure |
| BYOK agent/provider stack | Runtime keys/settings serialize separately from TTS and telephony |
| BYOK telephony | Twilio/Telnyx/Plivo/SignalWire/SIP credentials serialize under telephony |
| BYOK TTS | Cartesia/ElevenLabs/Inworld/Deepgram/custom TTS config serializes under TTS |
| Voice preview | `/v1/tts` returns playable audio |
| Log stream | `/v1/logs/stream` emits `event: log` rows |
| MCP `tail_logs` | Bounded polling returns new rows without leaking secrets |

## Number Purchase Test Safety

Tests should default to `numberStrategy: "default_pool"` or mocked number
inventory. Dedicated and premium purchase tests must be isolated, explicitly
enabled, and clearly labeled as billable.

Use environment flags such as:

```bash
export SUPAFONE_ALLOW_NUMBER_PURCHASES=0
export SUPAFONE_ALLOW_PREMIUM_NUMBERS=0
```

Only set them to `1` for intentional live billing tests.
