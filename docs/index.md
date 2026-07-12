# Supafone Labs

**Build complete voice agents with managed numbers, voices, stages, tools, and a second mind built in.**

```python
import supafone_labs

brain = supafone_labs.supercharge(my_agent)
```

Supafone Labs is the developer framework behind Supafone. You can create a
hosted Supafone agent from code with Supafone-managed phone numbers, managed
voices, built-in stages, tools, transcripts, recordings, web widgets, and
Supafone Pro call coaching. Or you can attach the same Labs layer to the voice
stack you already run.

Voice agents are brittle because they have *one brain on a stopwatch* -- every
thought competes with the latency budget of speech, so deliberation always
loses. Supafone Labs adds a **second, slower mind** that runs off the latency
path: it perceives the caller, remembers, retrieves, deduces intent and emotion,
catches mistakes, and silently coaches the live agent. And it **improves every
call** via gradient descent on its own prompts.

## One package, two main features

Supafone Labs gives you two product pillars:

- **Agent Factory** -- create a durable phone/web/campaign agent with
  `supafone-labs` and helpers such as
  `supafone.labs.agents.createInboundWithNumber()`. Supafone manages the phone
  number, agent/provider stack, TTS/STT/LLM defaults, multistage state machine,
  tools, recordings, transcripts, widget, usage, and Supafone Pro watcher. No
  developer vendor account is required in the default path.
- **Self-healing Labs watcher** -- keep Vapi, Retell, ElevenLabs, OpenAI
  Realtime, Grok, Ultravox, Gemini Live, Inworld, Deepgram, LiveKit, or another
  stack, then let Supafone Labs supervise and coach the live call. Ten frameworks
  accept a live silent directive; **Bland** can be supervised and scored but not
  coached live (closed live-call API). See
  [providers.md](providers.md) and `gitbook/framework-support.md`.

BYOK is optional and split into three lanes: agent/provider stack, telephony,
and TTS. Those lanes can be mixed with Supafone-managed defaults.

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
- [Providers & frameworks](providers.md) — Ultravox, Vapi, Retell, Pipecat,
  GPT-Realtime, Grok, LiveKit, ElevenLabs, Deepgram, Cartesia, Inworld, and the generic
  adapter.
