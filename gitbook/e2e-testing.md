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

## Fourteen-Runtime Injection Gate

The release gate does not infer success from configuration. It sends a current
provider event through the public facade, requires a belief and directive, and
then validates the exact compiled control payload for all fourteen runtimes:

```bash
cd supafone-labs
make test-provider-contracts PY=python3.12
```

The audited set is Supafone, Ultravox, Vapi, Retell, Bland, OpenAI Realtime,
Grok, Gemini Live, ElevenLabs, Deepgram Voice Agent, LiveKit Agents, Pipecat,
Cartesia Line, and Inworld Realtime. Bland and Cartesia deliberately assert a
safe no-action result because they do not expose a universal prompt-injection
channel. That is not counted as an injection pass.

`tests/test_cloud_phone_tester.py` separately runs the fourteen runtime labels
against all ten console telephony targets. Those 140 combinations must route
through the same managed PSTN grader, proving that target-carrier metadata does
not alter the test transport or the runtime injection contract.

Credentialed acceptance probes are separate:

```bash
python3.12 -m pytest --collect-only -q tests/test_live_injection_contracts.py
make test-live-injection PY=python3.12
```

The second command needs the relevant provider credentials and an active call
where required. Missing credentials produce a skip, never a pass. The live
probes send production-adapter payloads and wait for the provider's documented
acknowledgement or completed next turn.

| Live probe | Required environment |
| --- | --- |
| Ultravox | `ULTRAVOX_API_KEY`, `ULTRAVOX_LIVE_CALL_ID` |
| Vapi | `VAPI_CONTROL_URL` from an active monitor-enabled call |
| OpenAI Realtime | `OPENAI_API_KEY`; optional `OPENAI_REALTIME_MODEL` |
| Grok Voice Agent | `XAI_API_KEY`; optional `XAI_VOICE_MODEL` |
| Gemini Live | Google ADC plus `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GEMINI_LIVE_MODEL` |
| ElevenLabs Agents | `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID` |
| Deepgram Voice Agent | `DEEPGRAM_API_KEY`; optional `DEEPGRAM_LIVE_SETTINGS_JSON` |
| Inworld Realtime | `INWORLD_API_KEY`; optional socket URL/auth overrides |

Run one provider with `make test-live-injection PY=python3.12` plus a pytest
filter, for example `PYTEST_ADDOPTS="-k vapi"`.

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
