# 🧩 Framework Support (Silent Injection)

This is the definitive answer to one question: **which voice frameworks can the
Supafone watcher whisper into mid-call, and how?**

Silent injection means feeding the live agent hidden guidance it *acts on but
never speaks* — the supervisor's note slid across the desk. It is the mechanism
behind every watcher directive. Whether a framework can receive one depends
entirely on the door that vendor exposes, so the honest answer is per-framework,
not a blanket "works with everything."

## The two injection modes

Every supported framework uses one of two mechanisms:

- **Mode A — native silent event.** Integrated speech-to-speech models accept a
  vendor event that adds context to the running session **without triggering
  speech**. You send the event; the model reads it on its next turn and never
  reads it aloud.
- **Mode B — own the LLM.** For STT→LLM→TTS pipelines, Supafone plugs in as the
  LLM (custom-LLM / think stage) and **splices a `system`/`developer` message
  into the prompt before generation**. The pipeline never knows the difference;
  the agent simply behaves as guided.

Some frameworks expose both doors (marked **A+B**) — use whichever fits the
deployment.

## Possible — 10 frameworks

Each of these has a real injection door. The exact primitive is the vendor call
Supafone compiles the abstract directive into.

| Framework | Mode | Exact primitive |
| --- | :--: | --- |
| ![](https://www.google.com/s2/favicons?domain=ultravox.ai&sz=64) **Ultravox** | A | REST `POST /calls/{id}/send_data_message` with `urgency:"later"` — silent, no barge-in. **Live and proven in production today.** |
| ![](https://www.google.com/s2/favicons?domain=openai.com&sz=64) **OpenAI Realtime** | A | `conversation.item.create`, role `system`, `input_text` — and **no** `response.create` (so it lands as context, not a reply). |
| ![](https://www.google.com/s2/favicons?domain=x.ai&sz=64) **Grok (xAI)** | A | OpenAI-Realtime-compatible — the same item-inject primitive, base `wss://api.x.ai/v1/realtime`. |
| ![](https://www.google.com/s2/favicons?domain=ai.google.dev&sz=64) **Gemini Live** | A | `clientContent` with `turns:[{role:"user",...}]` and `turnComplete:false`. The role **must** be `user` (not `system`). |
| ![](https://www.google.com/s2/favicons?domain=elevenlabs.io&sz=64) **ElevenLabs** | A | `{"type":"contextual_update","text":...}` — silent, non-turn-taking. |
| ![](https://www.google.com/s2/favicons?domain=inworld.ai&sz=64) **Inworld** | A | OpenAI-Realtime-compatible — the same item-inject door. (Inworld also ships TTS voices; used purely as a voice it is tap-only like any TTS, but its conversational runtime is injectable.) |
| ![](https://www.google.com/s2/favicons?domain=vapi.ai&sz=64) **Vapi** | A+B | Live `add-message` with `triggerResponseEnabled:false`, **or** splice into the prompt when Supafone owns the custom LLM. |
| ![](https://www.google.com/s2/favicons?domain=retellai.com&sz=64) **Retell** | B | Custom-LLM websocket — splice a `system` message into `messages[]` on the turn you serve. |
| ![](https://www.google.com/s2/favicons?domain=deepgram.com&sz=64) **Deepgram** | A+B | `UpdatePrompt` event, **or** own the `think` LLM and splice the prompt. |
| ![](https://www.google.com/s2/favicons?domain=livekit.io&sz=64) **LiveKit** | B | You own the agent loop — inject into `chat_ctx` (`role:"assistant"`) in-process. |

## Impossible — 1 framework

- ![](https://www.google.com/s2/favicons?domain=bland.ai&sz=64) **Bland** — a closed box. The live-call API is **stop / listen / transfer
  only**: there is no channel to inject text mid-call, and no custom-LLM to own.
  The only Bland pattern is a **pull webhook configured before the call** —
  scripted checkpoints where Bland calls out to you at predefined moments. That
  is not live silent mid-turn injection. This is a **permanent vendor
  limitation**, not a Supafone gap: no amount of adapter work opens a door the
  vendor doesn't expose. You can still run a Bland agent under the watcher for
  post-call scoring and QA — it simply cannot receive live directives.

## Not conversational agents (n/a)

These aren't voice *agents*, so there is nothing to inject into:

- ![](https://www.google.com/s2/favicons?domain=cartesia.ai&sz=64) **Cartesia** — a **voice (TTS)**, not an agent. There is no reasoning loop to
  guide; Cartesia is used as the voice *on* another agent (e.g. Ultravox), and
  that host agent is where injection happens.
- ![](https://www.google.com/s2/favicons?domain=pipecat.ai&sz=64) **Pipecat** — a **DIY framework you assemble yourself**. Injection is trivial
  precisely because you own every step of the pipeline; there is no vendor door
  to document because you *are* the door. Splice guidance wherever you build the
  context.

## Honesty: possible ≠ turnkey today

Read this before quoting the matrix to a customer:

- **Injection is *possible* for all 10** frameworks above — each has a real,
  verified primitive. But **managed delivery is wired end-to-end only for
  Ultravox today.** The other nine are **supported via their native primitive**,
  with managed delivery rolling out and BYO (bring-your-own delivery) available
  now — you send the compiled action to the vendor yourself using the primitive
  in the table. Do not imply all ten are one-flag turnkey; only Ultravox is.
- **Running a real live test against any vendor needs that vendor's API key.**
  Free or trial tiers exist for every framework here **except OpenAI Realtime**,
  which is **paid with no free tier** — budget for it before you plan a live
  OpenAI Realtime test.

This matrix was verified against live vendor documentation and the Supafone
adapter code. See [Provider-Agnostic Framework](provider-agnostic-framework.md)
for the runtime that compiles one abstract decision into these primitives,
[Voice Watcher Framework](self-healing-watcher.md) for how directives are
produced, and [BYOK Providers](byok-providers.md) for bringing your own vendor
keys.
