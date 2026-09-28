# Supafone Supervisor

Supafone Supervisor runs beside an agent, off the realtime hot path. It observes
the call, returns a silent directive only when the live agent needs help, and
can score and QA the call after it ends.

For the practical developer view—multilingual continuity, provider switching,
cross-worker state, safety, telemetry, and failover—start with
[Production Voice AI: Daily Problems Supafone Solves](production-voice-ai-challenges.md).

## The first principle: the model speaking cannot fully supervise itself

Realtime voice models are optimized to answer quickly. A production supervisor
has a different job: watch patterns across turns, compare spoken claims with
tool ground truth, remember the operator's objective, notice a change in
language or urgency, and decide whether an intervention is worth interrupting
the agent's current trajectory.

Putting both jobs in one prompt creates a structural conflict. More reasoning
adds latency; less reasoning misses the moment. Supafone separates the roles:

```text
speaking model                         supervisor model
--------------                        ----------------
fast, natural response                slower cross-turn reasoning
owns the customer audio               never speaks to the customer
uses tools and follows stages         checks tool truth and stage progress
continues if supervisor is absent     emits a bounded silent directive or no-op
```

The supervisor is not a replacement agent and not a transcript summarizer. It
is a second control loop beside the call.

## The secret sauce: empathy as observable patterns

“Empathy” is not a personality adjective in the runtime. It is a changing set
of observable patterns that affect what the agent should do next:

- intent: what outcome the caller is actually trying to reach,
- urgency: whether waiting, escalation, or a shorter path matters,
- emotion: confusion, frustration, fear, confidence, or relief across turns,
- language: an explicit request or clear utterance in an approved language,
- trust: whether the agent acknowledged, verified, and followed through,
- progress: whether the current workflow stage is advancing or looping,
- truth: whether a booking, transfer, send, or CRM action really succeeded.

The Supervisor maintains that belief state over time. It does not route from a
name, accent, nationality, or presumed demographic. It waits for evidence,
compares the call with the operator's objective and tool results, and whispers
only when a short directive is likely to improve the outcome.

## The supervisor loop

```text
provider event
    -> normalize into one call contract
    -> update intent / emotion / language / stage / tool truth
    -> compare with objective, policy, and standing directive
    -> guard on evidence, tenant, provider, cooldown, and timeout
    -> compile one silent native instruction—or do nothing
    -> observe the next turn and verify whether it helped
    -> grade the completed call and improve the standing directive
```

This is why the framework can become more useful without taking over the live
audio path. The speaking agent stays fast; the supervisor accumulates context,
detects patterns, and closes the verification loop.

## Model agnostic by construction

The contract is between call events and supervisor directives, not between
Supafone and one model vendor. The speaking model, supervisor model, carrier,
STT, and TTS can be selected independently when the provider exposes the
required control surface.

Adapters translate provider-native events into the canonical state and compile
the resulting directive back to the provider's native silent channel. A team
can therefore keep Vapi, Retell, Ultravox, OpenAI Realtime, LiveKit, Pipecat,
Deepgram, ElevenLabs, or another compatible stack while retaining the same
supervision, QA, telemetry, and improvement loop. See
[Framework Support](framework-support.md) for exact capabilities and caveats.

The managed Ultravox-compatible Agent Factory is a compatibility lane for
provisioning a complete hosted agent with supervision already attached. Native
realtime Agent Factory is a separate first-class path for swapping among the
four native S2S provider families while keeping the carrier contract. Both
Agent Factory paths support coaching when enabled and configured. The Supervisor
contract also works when Supafone did not create the agent.

## Supervisor coaching across all five speaking families

Enable `supervisor: true` (Python `"supervisor": True`) when creating an agent,
or supply the existing managed/BYOK `supervisor` configuration. Supervisor is
independent of the speaking model: Ultravox, OpenAI, Gemini, Grok, and Hydra
all support hosted coaching. The same call-scoped coach is used for native
browser sessions and Supafone-managed, Twilio, Telnyx, Plivo, and SIP calls.
Each transport still needs its own configuration and live validation.

```ts
import { Supafone, HydraS2S } from "supafone-labs";

const client = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN! });
const engine = new HydraS2S(client, { model: "hydra-v1.1", voice: "maya" });
await engine.create({
  agentKey: "coached-intake",
  name: "Coached intake",
  description: "Understand the caller's request and verify the booking result.",
  supervisor: true,
});
```

```python
from supafone_labs import Supafone, OpenAIS2S

client = Supafone(api_key="sl_live_...")
engine = OpenAIS2S(client, model="gpt-realtime-2.1", voice="marin")
engine.create({
    "agentKey": "coached-intake",
    "name": "Coached intake",
    "description": "Understand the request and verify the booking result.",
    "supervisor": True,
})
```

### Observe, reason, return guidance

| Speaking path | Observation and delivery |
| --- | --- |
| Managed Ultravox, including compatible custom TTS | Existing call observation and deferred guidance delivery |
| Native OpenAI, Gemini, Grok | Provider transcripts and server tool outcomes inform a background coach; the model receives available guidance in a `check_guidance` tool result |
| Native Hydra | No native transcripts. `check_guidance(context)` supplies **model-reported context**; the coach checks it alongside server tool outcomes and returns guidance through the same tool result |

The native model is instructed to check for guidance at appropriate turn/tool
boundaries. Supervisor never speaks to the caller, forces a new response, or
interrupts the audio stream. A slow or unavailable Supervisor yields no
instruction and the call continues. Tool-result delivery is a request by the
speaking model, not a guarantee that it checks on every turn or follows a note.

Hydra context is explicitly recorded as `model_reported_context`, not a
transcript or an independently verified quote. Provider transcript paths use
`provider_transcript`. The server's actual tool result remains authoritative
for whether a booking or another operation succeeded. Hydra's persona and
voice remain fixed during the session; a coaching tool result does not rewrite
them.

### Supported, enabled, and ready are different

Native runtime metadata separates `supervisor: true` (supported) from
`supervisor_enabled` (the saved agent setting),
`supervisor_credentials_configured` (whether the Supervisor credential resolves),
`supervisor_observation`
(`provider_transcript` or `model_reported_context`), and
`supervisor_delivery: "tool_result"`. Support or an enabled setting does not
establish working credentials or a live coach. Even configured credentials
do not verify provider access or successful inference. Configure the selected managed
or BYOK Supervisor model separately from the speaking model, and inspect call
activity before treating coaching as running.

See [Supervisor Models: Managed and BYOK](supervisor-models.md) for model
configuration. The [standalone adapter matrix](framework-support.md) describes
external sessions; Hydra's hosted coaching does not imply a standalone Hydra
Supervisor adapter exists.

## Enable supervision

The SDK enables supervision in hosted agent creation by default. The selected
Supervisor model still needs configured managed or BYOK credentials. Native
coaching is available across the five speaking families; recording, QA artifacts,
and transcript availability remain separate runtime capabilities.

Python:

```python
from supafone_labs import Supafone

supafone = Supafone(api_key="sl_live_...")
```

TypeScript:

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN! });
```

Use the optional `supervisor` boolean to disable or re-enable this default.
Previous constructor options remain accepted as deprecated compatibility
aliases, so existing integrations continue to run unchanged.

## What Supafone monitors

- caller intent, urgency, language, and emotion,
- transcript contradictions,
- tool result failures,
- unverified booking, sending, pricing, or policy claims,
- compliance rules such as no fee quotes or no legal/medical advice,
- whether the agent is following the current standing directive.

## Transcript Source and STT Model

Supafone Supervisor does not force every provider through one speech-to-text model.
It selects exactly one transcript source for each call:

| Call path | Transcript source | Default model |
|---|---|---|
| Provider emits usable transcript events | The provider's transcript stream | The provider controls its STT model |
| Supafone Labs multilingual audio tap | Deepgram streaming STT | `nova-3`, `language=multi` |
| Host-integrated narrowband phone tap | The host's configured Deepgram consumer | Host controlled; Supafone's current Twilio reference defaults to `nova-2-phonecall` |

The narrowband phone default is deliberate: Twilio PSTN audio arrives as 8 kHz
mu-law. The multilingual SDK tap uses Nova-3 when language tagging and live
code-switching are required. Set `DEEPGRAM_MODEL` in a host deployment to
change its telephony-tap model. Do not run the Deepgram tap when the selected
agent provider already supplies the required transcript and language metadata;
that would duplicate turns and transcription cost.

## Enable on Hosted Agents

```json
{
  "labs": {
    "enabled": true,
    "model": "gemma"
  }
}
```

Equivalent legacy fields:

```json
{
  "voice_watcher": true,
  "voice_watcher_model": "gemma"
}
```

## Bring-Your-Stack Supervision

```python
from supafone_labs import SupafoneLabs

brain = SupafoneLabs(
    provider="vapi",
    llm="hosted",
    agent_label="intake",
)

result = await brain.observe(raw_event)

for action in result.actions:
    await deliver_to_voice_platform(action)
```

## Two ways the whisper lands

Every directive reaches the live agent through one of two silent-injection
modes, picked by what the framework exposes:

- **Mode A — native silent event.** Speech-to-speech models take a vendor event
  that adds context without triggering speech (Ultravox
  `send_data_message`/`inject_message`, OpenAI Realtime `conversation.item.create`
  with no `response.create`, ElevenLabs `contextual_update`, Gemini Live
  `clientContent`).
- **Mode B — own the LLM.** For STT→LLM→TTS pipelines Supafone plugs in as the
  LLM and splices a `system`/`developer` message into the prompt (Retell and
  LiveKit custom-LLM loops; Vapi and Deepgram support both modes).

The release gate covers fourteen runtimes. Twelve use native control or
developer-owned context, Bland remains observation-only, and Cartesia Line
requires an explicit host hook. Pipecat is a first-class developer-owned
context integration. The exact primitive and acceptance criterion live in
[Framework coverage](framework-support.md).

## Outcome Loop

Log the finished call:

```ts
await supafone.reportCall({
  session_id: "call-123",
  agent: "intake",
  score: 0.82,
  outcome: "clean",
  summary: "Caller scheduled a follow-up without unsupported claims.",
  nudges: 2,
  turns: 14,
  language: "en"
});
```

Or classify a transcript against an objective:

```bash
curl https://api.labs.supafone.ai/v1/calls/classify \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "call-123",
    "agent": "intake",
    "transcript": "caller: what do you charge?\nagent: I cannot quote fees here.",
    "nudges": 1
  }'
```

Improve the standing directive:

```ts
const improved = await supafone.optimizer.improve("intake");
console.log(improved.version, improved.text);
```

Read it:

```bash
curl "https://api.labs.supafone.ai/v1/optimizer/standing?agent=intake" \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"
```

## Degrade Safety

The supervisor is timeout-bounded and off the hot path. If the oracle fails,
times out, hits a balance or cap error, or decides no intervention is needed,
it returns no directive and the call continues normally.
