# The Sidecar Oracle

**A Provider-Agnostic Supervisor Harness for Real-Time Voice Agents**

Sam Savage · Supafone Labs · July 2026 · v1.1 · [PDF](/whitepaper.pdf) · [GitHub](https://github.com/samthedataman/supafone-labs)

## Abstract

Production voice agents operate under a hard latency budget: to sound human they must respond in well under a second, which structurally prevents the model that talks from also being the model that deliberates. We survey twenty-four published results across five research threads — dual-process agent architectures, the failure of intrinsic self-correction, external verifier and monitor models, inference-time multi-model oversight, and feedback-driven prompt optimization — and find they converge on a single architecture: a second, slower model running beside the conversation, off the latency path, injecting silent corrections through whatever control channel the serving platform natively exposes.

Our primary contribution is a runtime harness that makes supervision **provider-, LLM-, speech-to-speech-, and TTS-agnostic**: a canonical event algebra with per-provider adapters, a deterministic state reducer carrying ground-truth outcome signals, capability-aware compilation of one abstract correction decision into thirteen platforms' native controls, and degrade-safety semantics under which supervisor failure composes with the live call as a no-op. On top of the harness we describe an outcome-driven improvement loop — now including **SSR grading**, a nominal-scale judging flow that maps five ordered verdicts onto score distributions — in which a versioned standing directive is optimized OPRO-style from accumulated reports, without ever touching the operator's own system prompt.

## 1 · Introduction

A voice agent is one mind on a stopwatch. Perceived conversational quality collapses when response latency exceeds roughly a second, so every serving stack optimizes the talking model for speed. The consequence is architectural, not incidental: everything that determines whether a call succeeds is deliberation the latency budget forbids — reading distress in a caller's phrasing, noticing a mid-call language switch, catching the agent about to confirm a booking whose API call silently failed.

Human call centers solved the identical problem decades ago without retraining agents mid-shift: a supervisor listens silently and slides a note across the desk. The agent keeps talking; the note changes the call.

## 2 · A Meta-Analysis of Machine Supervision

Five threads of published evidence converge on the sidecar design:

| Design principle | Load-bearing evidence |
| --- | --- |
| Separate the talker from the deliberator | Talker-Reasoner (Christakopoulou et al. 2024); dual-process framing (Booch et al. 2020) |
| Supervision must be external | Intrinsic self-correction degrades (GSM8K 75.9→74.7; CSQA 75.8→38.1) while oracle-triggered correction gains (→84.3) (Huang et al. 2023) |
| The supervisor can be small | 6B verifier ≈ 30× generator scale (Cobbe et al. 2021); 7B critic ≈ ChatGPT (Shepherd); monitor recall 95% (Baker et al. 2025) |
| Supervise turns, not outcomes | Process supervision 78.2% vs outcome-only 72.4% on MATH (Lightman et al. 2023) |
| Never optimize against the monitor | Obfuscated reward hacking; monitor recall → 0 when judgments join the reward (Baker et al. 2025) |
| Improve prompts offline, from scores | OPRO, DSPy, TextGrad, ProTeGi, Darwin Gödel Machine |

The pivotal negative result is Huang et al.: a model reviewing its own answer with no external feedback reliably gets worse. The refinement mechanism works; self-generated judgment is the weak link. A supervisor must be a separate process with separate context and access to ground truth — in a voice call, the tool results and event stream that the runtime, not the model, holds.

## 3 · The Runtime Harness

### 3.1 The substrate problem

Voice-AI serving stacks fall into three classes: **speech-to-speech** agents (OpenAI Realtime, Grok Voice, Ultravox) with no out-of-band channel beyond a live session patch; **pipeline** agents (Vapi, Retell, ElevenLabs, Deepgram VA, Bland) where injection lands in LLM context between turns — when a channel exists at all; and **frameworks/components** (Pipecat, LiveKit; Cartesia, Inworld, raw STT) where the integrator owns the loop or nothing is injectable. Every class differs in event vocabulary, and wire formats drift quarterly. This heterogeneity, not the oracle, is the engineering problem.

### 3.2 Canonical events and the deterministic reducer

The harness defines a canonical event vocabulary and, per provider, an adapter supplying two pure functions — `parse: Raw → E*` and `compile: D × Σ → A` — where `D` is a provider-independent decision vocabulary and `A` the provider's native actions. A deterministic reducer folds events into runtime state Σ: the transcript with per-turn language tags, tool history, and decisively, **truth sub-state** — whether a requested booking was ever verified by a tool result, whether a promised delivery actually sent. Σ contains no model call, is ground truth by construction, and is replayable from the event log.

### 3.3 Capability-aware injection compilation

One abstract decision compiles across fourteen audited runtime integrations:

| Platform | Class | Compiled whisper |
| --- | --- | --- |
| Supafone / Ultravox | managed / S2S | deferred `user_text_message` |
| OpenAI Realtime / Inworld Realtime | S2S | system `conversation.item.create` |
| Grok Voice | S2S | per-response `response.create.instructions` |
| Gemini Live | S2S | `clientContent` user turn (system is invalid mid-session) |
| Vapi | pipeline | system `add-message` via live-call `controlUrl` |
| Retell (custom LLM) | pipeline | system message prepended to next turn |
| ElevenLabs Agents | pipeline | `contextual_update` (read, never spoken) |
| Deepgram Voice Agent | pipeline | `UpdatePrompt` (additive) |
| Pipecat | framework | `LLMMessagesAppendFrame`, `run_llm=false` |
| LiveKit Agents | framework | chat-context system append |
| Bland | pipeline | none — observation-only, honestly declared |
| Cartesia Line | component / agent hook | none until the agent handles a custom event |

### 3.4 The whisper path and degrade-safety

Off the hot path, the oracle maintains a belief state (identity, intent, emotion, language, urgency) and produces a directive under operator guardrails, gated by a confidence threshold. The entire oracle runs behind a timeout with catch-all semantics: **supervisor failure composes with the live call as the identity.** A stalled model, dead STT socket, or failed TTS backend cannot lengthen, alter, or end the call it shadows. The worst case is the status quo.

## 4 · The Improvement Loop

### 4.1 Grading calls against ground truth

Because Σ carries verified outcomes, calls are scored deterministically at session end: unverified bookings, unverified sends, unbacked claims, and dead-air events each subtract from a unit score. No LLM grades production calls where tool-verified ground truth exists.

### 4.2 SSR grading: nominal verdicts mapped to distributions *(new in v1.1)*

Where an LLM judge is required — builder test calls and objective classification — raw numeric scores are unreliable: judges are poorly calibrated as regressors but consistent as classifiers over ordered categories. The harness therefore grades on a five-level nominal scale, completing the sentence *"the agent did **{poorly | ok | good | great | perfectly}** at achieving the objective"* — overall and per named criterion.

Each label maps deterministically onto a canonical score and a discrete distribution over ten score buckets, spreading judge uncertainty around the label's center instead of pretending point precision. Aggregating many calls yields a **real score distribution** for the agent — the shape of performance, not just a pass rate — exposed at `GET /v1/objective/distribution` and rendered in the console.

The grading pipeline is implemented as a **LangGraph flow** with two nodes: `grade` (the only model call — the judge picks labels) and `map` (deterministic label → score + distribution). The flow degrades to sequential execution when LangGraph is absent, preserving the harness's no-op failure semantics.

### 4.3 The standing directive

The harness owns one prompt surface on every injectable platform: its own channel. The standing directive is a persistent, versioned coaching preamble injected at call start. An improvement step feeds recent scored reports — **including the SSR label distribution, weighted toward moving calls out of the lowest levels first** — and the current directive to a critic model, OPRO-style, yielding a new version with a stated rationale. The loop runs offline between calls, and its output is injected context, never a training signal — honoring the obfuscation result and verifier-gaming cautions. The operator's base prompt is untouched by design.

### 4.4 Observability as a product invariant

Every directive the oracle whispers is logged with its confidence, language, the caller's inferred emotional state, oracle latency, model, and billing cost; every optimization step records the reports it consumed; every SSR verdict stores both its label and mapped score. A system that whispers into production calls must be auditable end-to-end.

## 5 · The Agent Factory

The same control plane that supervises third-party stacks can provision complete agents: inbound receptionists and outbound sales agents with managed phone numbers, multistage conversations, tools, recordings, transcripts, and web widgets — collapsing the usual five-key integration (telephony, TTS, STT, LLM, supervision) into one API key. Supervision is on by default for factory agents; BYOK adapters cover teams that already own a stack.

## 6 · Limitations

(1) No controlled trial yet measures the sidecar's effect on business outcomes; the meta-analysis validates components in adjacent domains. (2) SSR grading applies where an LLM judge is required; deterministic scoring covers only tool-verified ground truth. (3) Whisper uptake is bounded by each platform's injection semantics; two platforms offer no channel. (4) Standing-directive optimization inherits OPRO's brittleness; directive length is bounded and version history retained because regressions are expected. (5) The oracle adds cost per turn; small-supervisor economics and per-second metering make it visible.

## 7 · Conclusion

Fast models need slow supervisors; supervision must be external; a small second model catches what the first cannot; its judgments must be injected, not optimized against; and prompt layers should improve offline from measured, distribution-shaped outcomes. What stood between that consensus and production voice AI was a substrate problem. A canonical event algebra, a deterministic ground-truth reducer, capability-aware compilation, and no-op failure semantics close that gap.

**The supervisor rides beside the call. It does not drive, and it cannot crash the bike.**

## References

Key sources: Christakopoulou et al. (Talker-Reasoner, 2024) · Huang et al. (self-correction fails, 2023) · Cobbe et al. (verifiers, 2021) · Lightman et al. (process supervision, 2023) · Baker et al. (monitor obfuscation, 2025) · Wang et al. (Shepherd, 2023) · Inoue et al. (AB-MCTS, 2025) · Cetin et al. (RL Teachers, 2025) · Zhang et al. (Darwin Gödel Machine, 2025) · Yang et al. (OPRO, 2023) · Khattab et al. (DSPy, 2023) · Yuksekgonul et al. (TextGrad, 2024) · Pryzant et al. (ProTeGi, 2023) · Bai et al. (Constitutional AI, 2022). Full citations in the [PDF](/whitepaper.pdf).
