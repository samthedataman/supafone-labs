# Self-Healing Watcher

The self-healing watcher is the Supafone Pro supervision layer. It observes the
call off the realtime hot path and returns a silent directive only when the live
agent needs help.

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

Platform actions compile to native controls such as Ultravox `inject_message`,
Vapi assistant overrides, ElevenLabs contextual updates, OpenAI Realtime
`session.update`, Pipecat context frames, or LiveKit chat context updates.

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

