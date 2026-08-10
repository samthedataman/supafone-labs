# SDK Parity

The Python and TypeScript SDKs should let developers do the same work with the
same vocabulary. Use camelCase in TypeScript and snake_case in Python, but keep
the payload concepts identical.

## Install

```bash
pip install "supafone-labs[all]"
npm i supafone-labs
```

## One-Line Framework

Python:

```python
import supafone_labs

brain = supafone_labs.supercharge(my_agent)
```

TypeScript developers usually call the hosted cloud/client surface directly:

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY!,
});
```

## Hosted Agent Factory

TypeScript:

```ts
const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake",
  name: "Northline intake",
  assistantName: "Maya",
  websiteUrl: "https://northline.example",
  number: { search: { areaCode: "415" } },
  labs: { enabled: true, model: "gemma" },
});
```

Python:

```python
agent = supafone.labs.agents.create_inbound_with_number({
    "agentKey": "northline-intake",
    "name": "Northline intake",
    "assistantName": "Maya",
    "websiteUrl": "https://northline.example",
    "number": {"search": {"areaCode": "415"}},
    "labs": {"enabled": True, "model": "gemma"},
})
```

Python also exposes camelCase aliases for developers copying TypeScript-shaped
configs:

```python
agent = supafone.labs.agents.createInboundWithNumber({
    "agentKey": "northline-intake",
    "name": "Northline intake",
    "number": {"search": {"areaCode": "415"}},
    "labs": {"enabled": True},
})
```

## One Contract, Four Entry Points

The stage planner and Agent Factory are public API capabilities. TypeScript is
one client, not the implementation boundary:

| Entry point | Preview a generated plan | Create the runnable agent |
| --- | --- | --- |
| REST | `POST /api/v1/labs/agent-plans` | `POST /api/v1/labs/agents` |
| TypeScript | `generateCallStages()` / `labs.agents.plan()` | `labs.agents.create()` |
| Python | `generate_call_stages()` / `labs.agents.plan()` | `labs.agents.create()` |
| MCP | `generate_call_stages` | hosted-agent creation tools |

Every entry point uses the same authenticated service, validation rules,
fallback behavior, JSON plan shape, and executable multi-stage runtime. A team
can prototype through MCP, ship the same operation through REST, and operate it
with either SDK without translating the contract.

## Method Map

| Capability | TypeScript | Python |
| --- | --- | --- |
| Create generic hosted agent | `supafone.labs.agents.create()` | `supafone.labs.agents.create()` |
| Preview hosted call plan | `supafone.generateCallStages()` / `labs.agents.plan()` | `supafone.generate_call_stages()` / `labs.agents.plan()` |
| Discover capabilities | `supafone.labs.capabilities()` | `supafone.labs.capabilities()` |
| List agent presets | `supafone.labs.presets.list()` | `supafone.labs.presets.list()` |
| List runtime tools | `supafone.labs.tools.list()` | `supafone.labs.tools.list()` |
| List/filter hosted voices | `supafone.labs.voices.list()` | `supafone.labs.voices.list()` |
| Read/configure Ultravox runtime | `supafone.labs.runtime.get/configure()` | `supafone.labs.runtime.get/configure()` |
| Create inbound agent | `createInbound()` | `create_inbound()` / `createInbound()` |
| Create outbound agent | `createOutbound()` | `create_outbound()` / `createOutbound()` |
| Create inbound + number | `createInboundWithNumber()` | `create_inbound_with_number()` / `createInboundWithNumber()` |
| Create outbound + number | `createOutboundWithNumber()` | `create_outbound_with_number()` / `createOutboundWithNumber()` |
| Search numbers | `supafone.labs.phoneNumbers.search()` | `supafone.labs.phone_numbers.search()` |
| Buy and assign number | `buyAndAssign()` | `buy_and_assign()` / `buyAndAssign()` |
| Configure telephony | `supafone.labs.telephony.configure()` | `supafone.labs.telephony.configure()` |
| List/fetch hosted calls | `supafone.labs.calls.list/get()` | `supafone.labs.calls.list/get()` |
| List/fetch/remove recordings | `supafone.labs.recordings.list/get/delete()` | `supafone.labs.recordings.list/get/delete()` |
| List/fetch transcripts | `supafone.labs.transcripts.list/get()` | `supafone.labs.transcripts.list/get()` |
| Usage | `supafone.usage()` | `supafone.usage()` |
| Log snapshot | `supafone.logs()` | `supafone.logs()` |
| Log stream | `supafone.streamLogs()` | `supafone.stream_logs()` / `streamLogs()` |
| Start browser WebRTC session | `supafone.startWebRtcCall()` / `startBrowserCall()` | `supafone.start_webrtc_call()` / `startWebRtcCall()` |
| Call a human from an owned agent | `supafone.callFromAgent()` | `supafone.call_from_agent()` |
| Grade an existing phone agent | `supafone.tester.gradeAgent()` | `supafone.tester.grade_agent()` |
| Fetch one call (live transcript) | `supafone.getCall()` | `supafone.get_call()` |
| Classify a finished call | `supafone.classifyCall()` | `supafone.classify_call()` |
| Auto post-call analysis | `postCallAnalysis: true` | `post_call_analysis=True` |
| Brand scan | `supafone.scanBrand()` | `supafone.scan_brand()` |
| Generate intake form | `supafone.generateIntakeForm()` | `supafone.generate_intake_form()` |
| Campaign lifecycle | `supafone.campaigns.create/get/list/update/launch/pause()` | same names, snake_case |
| Campaign live monitoring | `campaigns.live/getCall()` | `campaigns.live/get_call()` |
| Campaign config (YAML) | `campaigns.validateConfig/applyConfig/exportConfig/generateConfig()` | `campaigns.validate_config/apply_config/export_config/generate_config()` |
| E-sign documents | `campaigns.uploadSigningDocument/detectSignatureFields/setSignatureFields()` | `campaigns.upload_signing_document/detect_signature_fields/set_signature_fields()` |
| QA suites + SSR grading | `supafone.qa.generate/run/suite/history()` | `supafone.qa.generate/run/suite/history()` |
| Labs session login | `supafone.labsLogin()` | `supafone.labs_login()` |

## BYOK Parity

The SDKs support three distinct BYOK lanes:

| Lane | Examples |
| --- | --- |
| Agent/provider stack | Ultravox, Retell, Vapi, Bland, LiveKit, Pipecat, GPT Realtime, Grok |
| Telephony | Twilio, Telnyx, Plivo, SignalWire, SIP/custom trunks |
| TTS | Cartesia, ElevenLabs, Inworld, Deepgram, custom TTS |

TypeScript:

```ts
await supafone.labs.agents.createOutbound({
  agentKey: "speed-to-lead",
  name: "Speed to lead",
  labs: {
    enabled: true,
    mode: "byok",
    managedInfrastructure: false,
    stt: { provider: "deepgram", model: "nova-3" },
    llm: { provider: "anthropic", model: "claude-3-5-sonnet" },
    tts: { provider: "cartesia", voiceId: "sonic-warm" },
  },
  byok: {
    agentProvider: {
      provider: "ultravox",
      apiKey: process.env.ULTRAVOX_API_KEY!,
    },
    telephony: {
      mode: "byok",
      provider: "telnyx",
      credentials: {
        apiKey: process.env.TELNYX_API_KEY!,
        connectionId: process.env.TELNYX_CONNECTION_ID!,
        fromNumber: "+14155550123",
      },
    },
    tts: {
      provider: "cartesia",
      apiKey: process.env.CARTESIA_API_KEY!,
    },
  },
});
```

Python:

```python
supafone.labs.agents.create_outbound({
    "agentKey": "speed-to-lead",
    "name": "Speed to lead",
    "labs": {
        "enabled": True,
        "mode": "byok",
        "managedInfrastructure": False,
        "stt": {"provider": "deepgram", "model": "nova-3"},
        "llm": {"provider": "anthropic", "model": "claude-3-5-sonnet"},
        "tts": {"provider": "cartesia", "voiceId": "sonic-warm"},
    },
    "byok": {
        "agentProvider": {
            "provider": "ultravox",
            "apiKey": os.environ["ULTRAVOX_API_KEY"],
        },
        "telephony": {
            "mode": "byok",
            "provider": "telnyx",
            "credentials": {
                "apiKey": os.environ["TELNYX_API_KEY"],
                "connectionId": os.environ["TELNYX_CONNECTION_ID"],
                "fromNumber": "+14155550123",
            },
        },
        "tts": {
            "provider": "cartesia",
            "apiKey": os.environ["CARTESIA_API_KEY"],
        },
    },
})
```

Flat `providerKeys` remains supported for simple configs and older examples,
but new docs and UI should prefer the structured `byok` object so agent
platform, telephony, and TTS credentials do not get mixed together.

## Parity Notes

- TypeScript and Python both expose hosted agent creation helpers, phone-number
  lifecycle helpers, voice catalog/preview helpers, log snapshots, and log
  streaming.
- Both SDKs expose the hosted planner; REST and MCP expose the same operation.
- Agent creation defaults to hosted generation from the plain-language
  description and metadata. The resulting stages are validated and installed
  in the live runtime, not merely returned as suggestions.
- `callStages: false` / `"callStages": False` explicitly requests legacy
  single-prompt behavior. `"template"` selects the deterministic offline-safe
  planner; `"oracle"` selects hosted generation.
