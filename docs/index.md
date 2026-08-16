<p align="center">
  <img src="assets/supafone-logo.png" alt="Supafone" width="104" height="104" />
</p>

# Supafone Labs

**Production infrastructure for voice agents that need to work after the demo.**

## The problems we built it to solve

Voice agents are distributed systems: a realtime model, telephony, TTS, STT,
tools, retrieval, state, recordings, compliance, and post-call workflows must
behave like one product. The failure usually occurs between those layers.

| Problem | Innovation in the package |
| --- | --- |
| The speaking model must supervise itself | Voice Watcher and SecondMind run a separate, bounded supervision loop |
| Provider events and controls are incompatible | Fourteen audited adapters normalize one canonical runtime |
| Tool claims outrun tool results | Deterministic truth and consent state preserve verified outcomes |
| Every customer requires another architecture | Agent Factory creates editable stages, tools, voices, numbers, and artifacts |
| Testing is manual and subjective | Adversarial QA and SSR grading produce repeatable evidence |
| Call data is scattered across vendors | Durable activity APIs expose calls, plans, recordings, transcripts, and Watcher events |

See the complete [framework coverage matrix](providers.md) for the exact
support boundary of every runtime.

```python
import supafone_labs

brain = supafone_labs.supercharge(my_agent)
```

Supafone Labs is the developer framework behind Supafone. You can create a
hosted Supafone agent from code with Supafone-managed phone numbers, managed
voices, built-in stages, tools, transcripts, recordings, web widgets, and
Supafone Pro call coaching. Or you can attach the same Labs layer to the voice
stack you already run.

The speaking agent stays on the realtime path. Supafone's second mind observes
off that path, issues guidance only when evidence clears the configured gate,
and becomes a no-op when unavailable or uncertain.

## One package, two main features

Supafone Labs gives you two product pillars:

- **Agent Factory** -- create a durable phone/web/campaign agent with
  `supafone-labs` and helpers such as
  `supafone.labs.agents.createInboundWithNumber()`. Supafone manages the phone
  number, agent/provider stack, TTS/STT/LLM defaults, multistage state machine,
  tools, recordings, transcripts, widget, usage, and Supafone Pro watcher. No
  developer vendor account is required in the default path.
- **Self-healing Labs watcher** -- keep the voice stack you already run, then
  let Supafone Labs supervise and coach the live call. Fourteen audited runtime
  adapters normalize events; twelve expose native or developer-owned guidance
  paths, while Bland is observation-only and Cartesia Line requires an explicit
  host hook. See [providers.md](providers.md) and the
  [GitBook framework matrix](https://github.com/samthedataman/supafone-labs/blob/main/gitbook/framework-support.md).

BYOK is optional. Hosted delivery keeps agent-runtime, telephony, and TTS
credentials independent; the Watcher also supports separate STT and supervisor
LLM credentials. Every domain can be mixed with Supafone-managed defaults.

You can also run the deterministic open-source runtime and adapters locally
with your own keys.

`pip install supafone-labs` gives you both:

- **`supafone_labs.runtime`** — the deterministic, provider-agnostic voice **runtime** (the
  body). Canonical events, call state, truth/consent/watchdog policies, replay, and
  silent injection compiled to every provider. No LLM.
- **`supafone_labs`** — the LLM **oracle** + self-optimizing prompt engine on top of the
  runtime (the brain).

> The runtime is the rails and the train; the brain is the driver that gets smarter
> every trip. The split makes the brain **degrade-safe** — if it stalls, the call keeps
> running on the runtime's deterministic reflexes.

## Next

- [Quickstart](quickstart.md) — supercharge an agent in 60 seconds.
- [Hosted Agents API](hosted-agents-api.md) — create Supafone-hosted agents from
  code with managed voices, built-in stages, tools, widget snippets, and
  Supafone Pro.
- [Live language and voice routing](live-language-voice-routing.md) — opt-in
  same-call language changes with a matching voice and translated primary greeting.
- [Providers & frameworks](providers.md) — Ultravox, Vapi, Retell, Pipecat,
  GPT-Realtime, Grok, LiveKit, ElevenLabs, Deepgram, Cartesia, Inworld, and the generic
  adapter.
