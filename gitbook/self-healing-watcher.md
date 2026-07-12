# 🎧 Voice Watcher Framework

The Voice Watcher framework is the Supafone Pro supervision layer — the
self-healing watcher that runs beside every agent. It observes the call off the
realtime hot path and returns a silent directive only when the live agent needs
help, then scores and QAs the call after it ends.

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

Ten frameworks have a real injection door; **Bland does not** (closed live-call
API — no mid-call channel, no custom-LLM), and Cartesia/Pipecat are n/a. The
exact per-framework primitive, the honesty caveats, and which vendors need a
paid key live in [Framework Support (Silent Injection)](framework-support.md).

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
