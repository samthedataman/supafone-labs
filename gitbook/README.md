<p align="center">
  <img src=".gitbook/assets/supafone-logo.png" alt="Supafone" width="104" height="104" />
</p>

# Supafone Labs

**One speech-to-speech harness. Build an agent once, then choose its speaking model.**

Supafone's S2S harness is the shared runtime around a live speaking model: the
agent prompt, supported tools, conversation stages, server-side credentials,
and browser or phone connection. Agent Factory creates the durable agent that
runs inside that harness. Change its `realtime` selection to use another
supported model while keeping the same agent and phone configuration.

[Build your first S2S agent](quickstart.md) ·
[Open Agent Factory](https://app.supafone.ai/app/agents) ·
[Install Python or TypeScript](sdk-installation.md) ·
[Get a Supafone API key](https://labs.supafone.ai/console.html?mode=register)

## Native realtime Agent Factory

| Speaking provider | Supported model | Default voice |
| --- | --- | --- |
| OpenAI | `gpt-realtime-2.1` | `marin` |
| OpenAI | `gpt-live-1` | `marin` |
| Google | `gemini-3.1-flash-live-preview` | `Puck` |
| xAI | `grok-voice-latest` | `eve` |

Each model has an adapter for authenticated browser previews and phone calls
through **Supafone-managed phone, Twilio, Telnyx, Plivo, or SIP**. The catalog
reports supported integrations; workspace credentials, model access, carrier
setup, and a live test determine whether a particular deployment is ready.

Start with your Supafone API key. For the selected model, Supafone uses its
platform provider key when configured; you do not need to paste your own vendor
key. An encrypted account BYOK key overrides the platform key for that provider.
Check the runtime status before starting a call. A configured key alone does
not prove provider permissions or call quality.

## What the harness keeps together

| Layer | Your choice | Supafone's job |
| --- | --- | --- |
| Agent | Name, instructions, business knowledge, supported tools | Save one account-scoped agent and enforce tool authority |
| Stages | Intake → booking → confirmation | Preserve the fixed native stage contract and validate transitions |
| Speaking model | OpenAI, Google, or xAI catalog selection | Translate audio, model events, and tool calls through its adapter |
| Credentials | Managed platform key or optional BYOK | Keep secrets on the server and return masked readiness |
| Delivery | Browser, managed phone, or a supported BYO carrier | Connect the same agent through the selected transport |
| Client | Python, TypeScript, REST, or dashboard | Use the same hosted agent API |

A switch takes effect on a new session. Select a voice offered by the new model;
voices, latency, and model behavior are provider-specific. The harness does not
make every feature identical across providers.

## Choose the runtime for the job

| Path | Use it for | Current boundary |
| --- | --- | --- |
| **Native S2S Agent Factory** | Choose the speaking model and reuse supported stages/tools across browser and phone | Fixed three stages; no native recording, Supervisor coaching, human transfer, specialist-team handoff, DTMF, or public widget |
| **Managed compatibility Agent Factory** | Existing Ultravox-backed agents and workflows needing the broader hosted feature set | Used when `realtime` is omitted; managed or BYOK Ultravox |
| **Supafone Supervisor** | Add independent supervision to an existing supported agent stack | Adapter capability varies; separate from the native S2S transport |

The native harness supports knowledge lookup, lead capture, scheduling,
SMS/email, and configured custom tools through the server's allowed tools.
[Read the full feature boundaries](realtime-agent-factory.md#feature-boundaries)
before choosing the runtime for a customer workflow. Live language/voice routing
and the 1,600+ TTS voice catalog belong to the managed compatibility path;
native S2S uses each model's own voice list.

## Start building

1. [Quickstart](quickstart.md): create, preview, and switch an S2S agent.
2. [Agent Factory](agent-factory.md): understand the agent and runtime choices.
3. [Native S2S guide](realtime-agent-factory.md): model, credential, browser, and carrier contracts.
4. [Developer workflows](developer-workflows.md): repeat the workflow across your agents.
5. [Managed keys and BYOK](byok-providers.md): choose who supplies each credential.
6. [Framework coverage](framework-support.md): native model support versus Supervisor adapters.

## Cost comparison

See [Pricing and Credits](pricing-and-credits.md) for current managed-runtime
billing and credit behavior. BYOK usage is billed by the selected provider.
Do not assume that every model, carrier, or native S2S feature has the same
billing or inclusions as the managed compatibility stack.
