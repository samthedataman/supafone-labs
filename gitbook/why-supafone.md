# Why Supafone

**Choose the speaking model without rebuilding the agent. Keep Supervisor
alongside it.**

Supafone brings Ultravox, OpenAI, Gemini, Grok and Smallest AI Hydra into one
S2S routing hub. Agent Factory keeps your instructions, tools and call stages;
Supervisor adds a separate reasoning model that can guide the conversation.

Use one Supafone API key, or bring your own speaking-model and Supervisor
keys. The two choices are independent, so you can mix your own provider access
with Supafone's managed services. [Start with a supervised agent](quickstart.md)
or [connect your keys](byok-providers.md).

## Change the speaking model without rebuilding the agent

The S2S harness keeps a native agent's prompt, supported tools, custom stages,
server-side model credentials, and browser or phone transport together. Agent
Factory creates that agent, then the shared `SupafoneS2S` provider classes
choose Ultravox, OpenAI, Gemini, Grok, or Smallest AI Hydra. The native catalog
has six model choices; Ultravox retains its default managed runtime. Configured platform keys make BYOK optional. Model changes apply to new
sessions, with a voice valid for the selected model.

See the [shared interface](unified-s2s.md) and [native model support and limits](realtime-agent-factory.md).
Hydra has no live transcript stream and keeps its persona and voice fixed per
provider session. All five families share the workflow and reasoning layers;
external TTS, language profiles and carrier controls retain their own limits.
See [Shared runtime, Manager and teams](shared-agent-runtime.md).

## Problems we repeatedly encountered

| Problem | Failure in production | Innovation in the package |
| --- | --- | --- |
| Self-supervision | The speaking model misses cross-turn intent, emotion, workflow drift, and unsupported claims | **Supafone Supervisor** maintains a separate belief and directive loop off the audio hot path |
| Provider fragmentation | Every platform emits different transcript, tool, lifecycle, and control events | **Canonical event algebra and 14 audited adapters** create one runtime contract |
| Weak intervention controls | A generic prompt cannot safely alter an active call | **Capability-aware compilation** chooses native control, developer-owned context, host hook, observation, or no action |
| Tool hallucination | The agent says a booking, transfer, or delivery happened before the tool confirms it | **Truth state** separates verified outcomes from conversational language |
| Repeated agent engineering | Every customer brief becomes another prompt, router, stage graph, and webhook project | **Agent Factory** creates an inspectable plan plus managed delivery primitives |
| Manual testing | A few employee test calls miss the scenarios real callers produce | **Objective-driven adversarial QA** generates cases from the actual agent contract |
| No stable quality score | Generic LLM scores fluctuate without an operational target | **SSR grading** converts nominal verdicts into inspectable score distributions |
| Scattered operations | Calls, recordings, transcripts, and decisions live in separate vendor consoles | **Durable activity APIs and telemetry** expose one history to SDKs and product UIs |
| Multilingual discontinuity | Language changes duplicate transcripts, lose state, or use the wrong voice | **Transcript-authority rules and opt-in language/voice profiles** preserve one canonical call |
| Rebuilt customer infrastructure | Phone, WebRTC, SMS, campaigns, numbers, signing, and writebacks are implemented repeatedly | **Unified SDK, REST, and MCP surfaces** expose the surrounding operating system |

## The design response

```text
production call problem
  -> canonical event
  -> deterministic call state
  -> Supafone Supervisor belief and directive
  -> confidence, truth, and policy gate
  -> provider-aware compiler
  -> native action or safe no-op

The same call state also feeds replay, QA, telemetry, and optimization.
```

The architecture follows four rules:

1. **The live call remains primary.** Supervision never blocks the speaking
   agent.
2. **Facts and warmth remain separate.** Empathy cannot override tool truth,
   consent, or policy.
3. **Capability is explicit.** Supafone never pretends a provider supports a
   control it does not expose.
4. **Evidence drives improvement.** Calls can be replayed, graded, compared,
   and used to improve standing directives.

## What developers stop rebuilding

- Agent and stage planning
- Provider event normalization
- Mid-call supervision
- Truth and consent state
- TTS, STT, and telephony selection
- Phone and WebRTC delivery
- Recordings and transcripts
- Post-call classification
- Adversarial QA and grading
- Campaign, messaging, and artifact workflows
- Operational logs and activity APIs

Continue with [Framework coverage](framework-support.md) to see exactly how the
runtime maps onto each supported platform, then use the
[SDK quickstart](quickstart.md) to create or supervise an agent.
