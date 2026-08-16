# Voice Watcher and SecondMind

The Voice Watcher framework is the Supafone Pro supervision layer — the
self-healing watcher that runs beside every agent. It observes the call off the
realtime hot path and returns a silent directive only when the live agent needs
help, then scores and QAs the call after it ends.

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

The Watcher maintains that belief state over time. It does not route from a
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

The hosted Agent Factory is intentionally secondary: it is the fastest way to
provision a complete agent with the supervisor already attached. The defining
product is the supervisor contract, which also works when Supafone did not
create the agent.

## Run Agents Under the Voice Watcher (SDK client flag)

Since SDK 0.4.6 the SDK client takes a single `voice_watcher` flag. It is
**on by default**, so every agent the client provisions runs under the Voice
Watcher framework (live supervision + QA + call scoring). Set it to `false` to
get a raw agent with no watcher.

Python:

```python
from supafone_labs import Supafone

supafone = Supafone(api_key="sl_live_...", voice_watcher=True)   # default on
raw = Supafone(api_key="sl_live_...", voice_watcher=False)       # raw agent, no watcher
```

TypeScript:

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN!, voiceWatcher: true });  // default on
const raw = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN!, voiceWatcher: false });       // raw agent, no watcher
```

When set, the SDK injects `voice_watcher` into the agent-create payload (and
mirrors it into a `labs` block when one is present). The TypeScript client also
accepts `voice_watcher` (snake case); both SDKs keep a deprecated `labs` alias
for older callers.

## What It Watches

- caller intent, urgency, language, and emotion,
- transcript contradictions,
- tool result failures,
- unverified booking, sending, pricing, or policy claims,
- compliance rules such as no fee quotes or no legal/medical advice,
- whether the agent is following the current standing directive.

## Transcript Source and STT Model

Voice Watcher does not force every provider through one speech-to-text model.
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

The watcher is timeout-bounded and off the hot path. If the oracle fails,
times out, hits a balance or cap error, or decides no intervention is needed,
it returns no directive and the call continues normally.
