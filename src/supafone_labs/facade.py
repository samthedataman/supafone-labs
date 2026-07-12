"""The one-line developer surface: supafone_labs.supercharge(agent).

Hides the runtime, adapters, oracle, and injection plumbing behind a single call so any
voice agent gains a second mind with no knowledge of the internals.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from supafone_labs.config import Settings, get_settings
from supafone_labs.llm.registry import get_default_provider
from supafone_labs.oracle.policy import OracleWorkflow
from supafone_labs.oracle.session import OracleSession
from supafone_labs.runtime.adapters import (
    BlandAdapter,
    CartesiaAdapter,
    DeepgramAdapter,
    ElevenLabsAdapter,
    GeminiLiveAdapter,
    GenericWebhookAdapter,
    GPTRealtimeAdapter,
    GrokAdapter,
    InworldAdapter,
    LivekitAdapter,
    PipecatAdapter,
    RetellAdapter,
    UltravoxAdapter,
    VapiAdapter,
)
from supafone_labs.runtime.core.decision import ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.state import RuntimeState, build_initial_state
from supafone_labs.types import BeliefState, Directive, directive_to_decision

# Scenario presets pre-tune the oracle's guardrails/lens for common verticals.
SCENARIO_PRESETS: dict[str, list[str]] = {
    "legal_intake": [
        "Don't quote fees",
        "No legal advice",
        "Acknowledge injury/distress before logistics",
    ],
    "medical_frontdesk": [
        "No clinical advice",
        "Protect PHI — verify identity before sharing",
        "Escalate emergencies to 911 immediately",
    ],
    "sales_outbound": ["Lead with value", "Respect do-not-call / opt-out signals"],
    "support": ["Confirm you understood before resolving"],
    "generic": [],
}


def _default_adapters() -> list[Any]:
    return [
        UltravoxAdapter(),
        VapiAdapter(),
        BlandAdapter(),
        GPTRealtimeAdapter(),
        GeminiLiveAdapter(),
        RetellAdapter(),
        GrokAdapter(),
        ElevenLabsAdapter(),
        DeepgramAdapter(),
        PipecatAdapter(),
        LivekitAdapter(),
        CartesiaAdapter(),
        InworldAdapter(),
        GenericWebhookAdapter(),
    ]


# --- pluggable live-data feed --------------------------------------------------

async def _maybe_await(fn: Callable[[RuntimeState], Any], state: RuntimeState) -> str:
    try:
        result = fn(state)
        if asyncio.iscoroutine(result):
            result = await result
        return str(result or "")
    except Exception:
        return ""


class _Source:
    async def fetch(self, state: RuntimeState) -> str:  # pragma: no cover - overridden
        return ""


class CallerHistory(_Source):
    """Feed source for who the caller is / prior interactions. Wraps a callable(state)->str."""

    def __init__(self, loader: Callable[[RuntimeState], Any]) -> None:
        self._loader = loader

    async def fetch(self, state: RuntimeState) -> str:
        return await _maybe_await(self._loader, state)


class Knowledge(_Source):
    """Feed source for firm/product knowledge (RAG). Wraps a callable(state)->str."""

    def __init__(self, retriever: Callable[[RuntimeState], Any]) -> None:
        self._retriever = retriever

    async def fetch(self, state: RuntimeState) -> str:
        return await _maybe_await(self._retriever, state)


class CRM(_Source):
    """Feed source for case/lead data. Wraps a callable(state)->str."""

    def __init__(self, client: Callable[[RuntimeState], Any]) -> None:
        self._client = client

    async def fetch(self, state: RuntimeState) -> str:
        return await _maybe_await(self._client, state)


@dataclass
class Feed:
    """The live-data spine the oracle draws on, plus standing guardrails."""

    context: list[Any] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)

    async def gather(self, state: RuntimeState) -> str:
        chunks: list[str] = []
        for src in self.context:
            try:
                txt = await src.fetch(state) if hasattr(src, "fetch") else await _maybe_await(src, state)
            except Exception:
                txt = ""
            if txt:
                chunks.append(txt)
        return "\n".join(chunks)


# --- result --------------------------------------------------------------------

@dataclass
class SuperchargeResult:
    """What one observe() turn produced."""

    events: list[Any] = field(default_factory=list)
    belief: Optional[BeliefState] = None
    directive: Optional[Directive] = None
    decision: Optional[RuntimeDecision] = None
    actions: list[ProviderAction] = field(default_factory=list)
    injected: bool = False


# --- provider auto-detection ---------------------------------------------------

_PROVIDER_HINTS = {
    "ultravox": "ultravox",
    "vapi": "vapi",
    "bland": "bland",
    "retell": "retell",
    "grok": "grok",
    "elevenlabs": "elevenlabs",
    "11labs": "elevenlabs",
    "deepgram": "deepgram",
    "pipecat": "pipecat",
    "livekit": "livekit",
    "cartesia": "cartesia",
    "inworld": "inworld",
    # generic hints LAST so specific names above win class-name matching
    # (e.g. "GrokRealtimeBot" is grok, not gpt_realtime)
    "gpt": "gpt_realtime",
    "openai": "gpt_realtime",
    "realtime": "gpt_realtime",
}


def _detect_provider(agent: Any) -> Optional[str]:
    if agent is None:
        return None
    for attr in ("provider", "provider_name", "platform"):
        value = getattr(agent, attr, None)
        if isinstance(value, str) and value:
            key = value.lower()
            return _PROVIDER_HINTS.get(key, key)
    name = type(agent).__name__.lower()
    for hint, provider in _PROVIDER_HINTS.items():
        if hint in name:
            return provider
    return None


def _resolve_injector(agent: Any) -> Optional[Callable[[Any], Any]]:
    if agent is None:
        return None
    for method in ("inject", "send_system", "add_message", "inject_message", "whisper"):
        fn = getattr(agent, method, None)
        if callable(fn):
            return fn
    return None


# --- the facade ----------------------------------------------------------------

class SupafoneLabs:
    """A live second mind bound to one agent/provider. Feed it events; it whispers back."""

    def __init__(
        self,
        *,
        provider: Optional[str] = None,
        agent: Any = None,
        adapters: Optional[list[Any]] = None,
        config: Optional[Settings] = None,
        feed: Optional[Feed] = None,
        scenario: Optional[str] = None,
        mode: str = "apply",
        oracle: Optional[OracleSession] = None,
        injector: Optional[Callable[[Any], Any]] = None,
        tts: Any = None,
        llm: Any = None,
        oracle_model: Optional[str] = None,
        oracle_instructions: Optional[str] = None,
        belief_prompt: Optional[str] = None,
        directive_prompt: Optional[str] = None,
        inject_via: Optional[str] = None,
        telemetry: bool = True,
        post_call_analysis: bool = False,
        agent_label: str = "default",
    ) -> None:
        self.config = config or get_settings()
        self.mode = mode
        self.feed = feed
        self.agent = agent
        self.default_provider = provider or _detect_provider(agent) or "ultravox"
        # Real deployments often TAP one source but WHISPER to another —
        # e.g. transcripts from a Twilio->Deepgram audio fork, injection into
        # the Ultravox/Vapi agent actually running the call.
        self.inject_via = inject_via
        self.telemetry = telemetry
        # post_call_analysis=True: when a session ends, the finished call is
        # automatically classified against the agent's objective — generating
        # labels (achieved/missed, per-criterion verdicts, failure reasons) —
        # and the enriched report is filed instead of the plain one. Results
        # land in self.analyses / self.last_analysis. Billed one oracle call
        # per analyzed call; falls back to the plain report on any failure.
        self.post_call_analysis = post_call_analysis
        self.analyses: dict[str, dict] = {}
        self.last_analysis: Optional[dict] = None
        # The self-optimizing loop: calls are scored + reported under this
        # label, and its hosted standing directive is injected at call start.
        self.agent_label = agent_label
        self._standing_loaded = False
        self._nudge_counts: dict[str, int] = {}

        guardrails = list(SCENARIO_PRESETS.get(scenario or "generic", []))
        if feed and feed.guardrails:
            guardrails.extend(feed.guardrails)

        # llm: a provider name ("anthropic" | "openai" | "xai" | "hosted" |
        # "fake"), a ready LLMProvider instance, or None. With only a model
        # given, the serving provider is inferred from the model id — so
        # SupafoneLabs(oracle_model="gpt-4.1-mini") just works.
        if isinstance(llm, str):
            from supafone_labs.llm.registry import get_provider

            llm = get_provider(llm)
        elif llm is None and oracle is None and oracle_model:
            from supafone_labs.config import provider_for_model
            from supafone_labs.llm.registry import get_provider

            inferred = provider_for_model(oracle_model)
            if inferred:
                llm = get_provider(inferred)
        self.oracle = oracle or OracleSession(
            provider=llm or get_default_provider(),
            config=self.config,
            guardrails=guardrails,
            model=oracle_model,
            instructions=oracle_instructions,
            belief_prompt=belief_prompt,
            directive_prompt=directive_prompt,
        )
        self.workflow = OracleWorkflow(self.oracle, threshold=self.config.confidence_threshold)

        from supafone_labs.runtime.core.runtime import AdheraRuntime  # local: avoid heavy import cost

        self.runtime = AdheraRuntime(workflow=self.workflow, adapters=adapters or _default_adapters())
        self._states: dict[str, RuntimeState] = {}
        self._injector = injector or _resolve_injector(agent)
        self._tts = tts

    @property
    def tts(self) -> Any:
        """Supafone Labs' own TTS (lazy): hosted on pro, BYO keys on free, fake offline."""
        if self._tts is None:
            from supafone_labs.tts import SupafoneLabsTTS  # local: keep import cost off the hot path

            self._tts = SupafoneLabsTTS()
        return self._tts

    async def speak(self, text_or_directive: Any = None) -> bytes:
        """Voice a directive (default: the last buffered one) or arbitrary text as audio bytes."""
        target = text_or_directive
        if target is None:
            target = next(reversed(self.oracle._buffer.values()), None) if self.oracle._buffer else ""
        if hasattr(target, "composed_text"):
            target = target.composed_text()
        return await self.tts.synthesize(str(target or ""))

    def _state_for(self, raw_event: dict, provider: str) -> tuple[str, RuntimeState]:
        sid = str(raw_event.get("session_id") or raw_event.get("call_id") or "session")
        state = self._states.get(sid)
        if state is None:
            state = build_initial_state(provider=provider, session_id=sid)
            self._states[sid] = state
        return sid, state

    async def observe(self, raw_event: dict, provider: Optional[str] = None) -> SuperchargeResult:
        """Ingest one provider event, run the oracle off-path, and (optionally) inject silently."""
        provider = provider or self.default_provider
        if provider not in self.runtime.adapters and "generic" in self.runtime.adapters:
            provider = "generic"  # unknown platform: best-effort webhook mapping
        sid, state = self._state_for(raw_event, provider)
        try:
            next_state, events, _decisions = await self.runtime.ingest_raw(
                provider=provider, raw_event=raw_event, state=state
            )
        except Exception:
            return SuperchargeResult()
        self._states[sid] = next_state

        await self._ensure_standing()
        self._maybe_finish_session(sid, next_state, events)

        result = SuperchargeResult(events=events)
        oracle_started = time.monotonic()
        directive = await self.oracle.observe(next_state)
        oracle_ms = (time.monotonic() - oracle_started) * 1000
        result.belief = self.oracle.last_belief
        result.directive = directive
        if directive is None:
            return result

        decision = directive_to_decision(directive, self.config.confidence_threshold)
        if decision is None:
            self._report_nudge(sid, provider, directive, next_state, oracle_ms, injected=False)
            return result
        result.decision = decision
        try:
            if self.inject_via and self.inject_via in self.runtime.adapters:
                adapter = self.runtime.adapters[self.inject_via]
                result.actions = await adapter.compile(decision, next_state)
            else:
                result.actions = await self.runtime.compile(state=next_state, decision=decision)
        except Exception:
            result.actions = []
        if self.mode == "apply" and self._injector and result.actions:
            result.injected = await self._apply(result.actions)
        self._report_nudge(sid, provider, directive, next_state, oracle_ms, injected=result.injected)
        return result

    async def _ensure_standing(self) -> None:
        """Once per brain: pull the self-optimized standing directive and fold it in."""
        if self._standing_loaded or not self.telemetry:
            return
        self._standing_loaded = True
        try:
            from supafone_labs.telemetry import fetch_standing

            standing = await fetch_standing(self.agent_label)
            if standing:
                suffix = f"\n\nStanding directive (self-optimized v-latest):\n{standing}"
                self.oracle.directive_gen.system_prompt += suffix
                self.oracle.belief_engine.system_prompt += suffix
        except Exception:
            pass

    def report(self, session_id: str) -> Any:
        """Deterministic post-call report for one session (also auto-sent on session end)."""
        from supafone_labs.postcall import score_call

        state = self._states.get(session_id)
        if state is None:
            return None
        return score_call(
            state, nudges=self._nudge_counts.get(session_id, 0), agent=self.agent_label
        )

    def _maybe_finish_session(self, session_id: str, state: RuntimeState, events: list) -> None:
        """On session end: score the call and report it (fire-and-forget).
        With post_call_analysis=True the call is classified instead — labels
        generated against the objective, enriched report filed server-side."""
        if not any(getattr(e, "type", "") == "session.ended" for e in events):
            return
        try:
            report = self.report(session_id)
            if report is None or not self.telemetry:
                return
            if self.post_call_analysis:
                self._schedule_post_call_analysis(report, state)
                return
            from supafone_labs.telemetry import report_call_soon

            report_call_soon(
                session_id=report.session_id,
                agent=report.agent,
                score=report.score,
                outcome=report.outcome,
                summary=report.summary,
                nudges=report.nudges,
                turns=report.turns,
                language=report.language,
            )
        except Exception:
            pass

    def analysis(self, session_id: str) -> Optional[dict]:
        """The post-call analysis labels for one session (None until classified)."""
        return self.analyses.get(session_id)

    def _schedule_post_call_analysis(self, report: Any, state: RuntimeState) -> None:
        """Fire-and-forget post-call analysis: classify the finished call
        against the agent's objective (generating labels + the enriched
        report), falling back to the plain deterministic report on failure.
        Never blocks the call path, never raises."""
        import asyncio

        from supafone_labs.telemetry import classify_call_report, report_call

        transcript = "\n".join(f"{t.actor}: {t.text}" for t in state.transcript if t.text)
        truth = state.truth_state
        ground_truth = {
            "booking_requested": truth.booking_requested,
            "booking_verified": truth.booking_verified,
            "delivery_requested": truth.delivery_requested,
            "delivery_verified": truth.delivery_verified,
            "end_call_claims_verified": truth.end_call_claims_verified,
            "unverified_claims": list(truth.last_unverified_claims),
        }

        async def _run() -> None:
            analysis = await classify_call_report(
                session_id=report.session_id,
                agent=report.agent,
                transcript=transcript,
                ground_truth=ground_truth,
                nudges=report.nudges,
            )
            if analysis:
                self.analyses[report.session_id] = analysis
                self.last_analysis = analysis
                return
            # Analysis unavailable (offline / no oracle) — the plain
            # zero-billed deterministic report still lands.
            await report_call(
                session_id=report.session_id,
                agent=report.agent,
                score=report.score,
                outcome=report.outcome,
                summary=report.summary,
                nudges=report.nudges,
                turns=report.turns,
                language=report.language,
            )

        try:
            asyncio.get_running_loop().create_task(_run())
        except RuntimeError:
            pass

    def _report_nudge(
        self,
        session_id: str,
        provider: str,
        directive: Any,
        state: RuntimeState,
        oracle_ms: float,
        *,
        injected: bool,
    ) -> None:
        """Fire-and-forget: log this nudge to the cloud console with full granularity.
        Never blocks the call path, never raises."""
        if directive is None:
            return
        self._nudge_counts[session_id] = self._nudge_counts.get(session_id, 0) + 1
        if not self.telemetry:
            return
        try:
            from supafone_labs.telemetry import report_nudge_soon

            belief = self.oracle.last_belief
            report_nudge_soon(
                session_id=session_id,
                provider=self.inject_via or provider,
                text=directive.composed_text(),
                confidence=float(getattr(directive, "confidence", 0.0)),
                injected=injected,
                kind=str(getattr(getattr(directive, "kind", ""), "value", "") or getattr(directive, "kind", "")),
                language=str(getattr(directive, "language", "") or getattr(belief, "language", "") or ""),
                emotion=str(getattr(belief, "emotional_state", "") or ""),
                intent=str(getattr(belief, "intent", "") or ""),
                urgency=float(getattr(belief, "urgency", 0.0) or 0.0),
                latency_ms=round(oracle_ms, 1),
                model=str(self.oracle.config.oracle_model),
                turns=len(state.transcript),
            )
        except Exception:
            pass

    async def _apply(self, actions: list[ProviderAction]) -> bool:
        try:
            outcome = self._injector(actions)  # type: ignore[misc]
            if asyncio.iscoroutine(outcome):
                await outcome
            return True
        except Exception:
            return False


def supercharge(
    agent: Any = None,
    *,
    provider: Optional[str] = None,
    feed: Optional[Feed] = None,
    scenario: Optional[str] = None,
    mode: str = "apply",
    config: Optional[Settings] = None,
    adapters: Optional[list[Any]] = None,
    injector: Optional[Callable[[Any], Any]] = None,
    oracle: Optional[OracleSession] = None,
    tts: Any = None,
    llm: Any = None,
    oracle_model: Optional[str] = None,
    oracle_instructions: Optional[str] = None,
    belief_prompt: Optional[str] = None,
    directive_prompt: Optional[str] = None,
) -> SupafoneLabs:
    """Give any voice agent a second mind in one line. Provider is auto-detected from `agent`."""
    return SupafoneLabs(
        provider=provider,
        agent=agent,
        adapters=adapters,
        config=config,
        feed=feed,
        scenario=scenario,
        mode=mode,
        injector=injector,
        oracle=oracle,
        tts=tts,
        llm=llm,
        oracle_model=oracle_model,
        oracle_instructions=oracle_instructions,
        belief_prompt=belief_prompt,
        directive_prompt=directive_prompt,
    )


def attach(agent: Any, feed: Optional[Feed] = None, **kwargs: Any) -> SupafoneLabs:
    """Alias for supercharge()."""
    return supercharge(agent, feed=feed, **kwargs)
