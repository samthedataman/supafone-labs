# Providers & frameworks

> **Injectable at a glance:** ten frameworks accept a silent directive
> (Ultravox, OpenAI Realtime, Grok, Gemini Live, ElevenLabs, Inworld, Vapi,
> Retell, Deepgram, LiveKit); **Bland cannot** (closed live-call API), and
> Cartesia/Pipecat are n/a. The definitive matrix with modes, exact primitives,
> and honesty caveats is [gitbook/framework-support.md](../gitbook/framework-support.md).
> This page is the per-adapter capability + test-receipt detail.

Supafone Labs plugs into **almost any** voice agent — the runtime normalizes every provider
into one canonical event vocabulary and compiles one abstract `inject_hidden_instruction`
decision into each provider's native control. The one exception is Bland, whose live-call
API exposes no injection door at all. Three integration kinds:

- **Agent platforms** — the provider runs the agent and emits call events (webhook or
  realtime); you inject via their control API. *(Ultravox, Vapi, Bland, Retell,
  GPT-Realtime, Grok, ElevenLabs, Deepgram Voice Agent)*
- **Agent frameworks** — you build the pipeline; you tap frames and inject a context
  frame. *(Pipecat, LiveKit Agents)*
- **TTS/STT components** — not agents themselves; the adapter maps their STT transcripts
  into canonical events (tap-only — there's nothing to inject into a raw TTS engine).
  *(Cartesia, Inworld)*

## Capability matrix

`ProviderCapabilities` declares what each provider supports, so Supafone Labs picks the
best injection path automatically.

| Provider | Kind | Hidden-instruction inject | Mid-call prompt patch | Tool interception | Transcript stream |
|---|---|:--:|:--:|:--:|:--:|
| Ultravox | agent | Yes | Yes | Yes | Yes |
| Vapi | agent | Yes | Yes | Yes | Yes |
| Bland | agent | — | — | — | Yes⁶ |
| Retell | agent | Yes² | Yes | Yes | Yes |
| GPT-Realtime | agent | Yes¹ | Yes | Yes | Yes |
| Grok Realtime | agent | Yes¹ | Yes | Yes | Yes |
| ElevenLabs Conversational AI | agent | Yes³ | Yes | Yes | Yes |
| Deepgram Voice Agent | agent | Yes⁴ | Yes⁴ | Yes | Yes |
| Pipecat | framework | Yes⁵ | Yes | Yes | Yes |
| LiveKit Agents | framework | Yes⁵ | Yes | Yes | Yes |
| Cartesia | TTS/STT | — | — | — | Yes (STT) |
| Inworld | TTS⁷ | — | — | — | — |
| Generic | webhook | configurable | configurable | configurable | configurable |

¹ Silent context is injected via `conversation.item.create` (role `system`,
  `input_text`) with **no** following `response.create`, so it lands as context
  the model reads but does not speak. A `session.update` prompt patch is the
  alternative mid-call path. Grok is OpenAI-Realtime-compatible (same primitive,
  base `wss://api.x.ai/v1/realtime`).
² Retell's custom-LLM loop lets you inject directly into the model context each turn.
³ ElevenLabs supports `contextual_update` — text the agent reads but does not speak.
⁴ Deepgram Voice Agent's silent primitive is the `UpdatePrompt` event (context
  the agent reads, not speaks); you can also own the `think` LLM and splice the
  prompt directly. (`InjectAgentMessage` makes the agent *speak* a line, so it is
  not a silent inject.)
⁵ Frameworks inject by appending a system/context frame to the live pipeline.
⁶ Bland streams live speech lines via `webhook_events` and a full transcript in the
  end-of-call webhook, but documents **no** mid-call injection/prompt API — tap-only.
⁷ This row is the Inworld **TTS voice** (tap-only, like any voice). Inworld also
  ships a **conversational runtime** that is OpenAI-Realtime-compatible — that
  runtime *is* injectable via the same item-inject door (Mode A). See
  [gitbook/framework-support.md](../gitbook/framework-support.md).

> **Honesty note:** all 13 adapters ship with unit tests (parse + inject-compile +
> capability consistency, ~180 tests), and the schemas are backed by two kinds of
> receipts:
>
> - **Verified against live APIs** (`pytest -m live`): Deepgram STT + Aura TTS,
>   Ultravox REST messages, ElevenLabs Conversational AI (real session; real
>   `contextual_update` accepted), Cartesia Ink STT (real transcript frames), and
>   Inworld TTS.
> - **Verified against official docs (July 2026)**: Retell, Vapi (nested `message`
>   envelope, `tool-calls`), Bland (end-of-call payload + `webhook_events` lines),
>   OpenAI Realtime **GA** names (`response.output_audio_transcript.*`), xAI Grok
>   Voice Agent (`conversation.item.input_audio_transcription.updated`), LiveKit
>   Agents event dataclasses (source-checked), Pipecat frames (source-checked),
>   Deepgram Voice Agent (`UpdatePrompt{prompt}`, `InjectAgentMessage{message}`).
>
> Vapi/Retell/Bland have not been exercised against a live account (no keys) — only
> against their current documented shapes.
>
> **S2S vs pipeline:** speech-to-speech agents (GPT-Realtime, Grok, Ultravox) are
> audio-native — the only whisper path is a live prompt patch (`session.update`).
> Pipeline agents (Vapi, Bland, Retell, ElevenLabs, Deepgram Voice Agent) run
> STT → LLM → TTS, so the whisper lands in the LLM context between turns. Raw speech
> components (Cartesia, Inworld, Deepgram listen) are tap-only by construction.

## Writing an adapter

An adapter implements two methods plus a capability declaration:

```python
from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import DecisionKinds, ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState


class MyProviderAdapter(BaseAdapter):
    provider_name = "myprovider"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(supports_mid_call_prompt_patch=True)

    async def parse_event(self, raw_event: dict) -> list:
        if raw_event.get("type") == "transcript":
            return [make_event(
                EventTypes.CALLER_TRANSCRIPT_FINAL,
                session_id=self._session_id(raw_event),
                provider=self.provider_name,
                actor="caller",
                text=raw_event.get("text", ""),
                data=raw_event,
            )]
        return []

    async def compile(self, decision: RuntimeDecision, state: RuntimeState) -> list[ProviderAction]:
        if decision.kind == DecisionKinds.INJECT_HIDDEN_INSTRUCTION:
            return [ProviderAction(
                provider=self.provider_name,
                kind="inject",
                payload={"text": decision.payload["text"]},
            )]
        return []
```

Drop it in `src/supafone_labs/runtime/adapters/`, add a sample-payload test, and it works
with the entire Supafone Labs brain for free.
