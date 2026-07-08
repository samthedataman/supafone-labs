from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

from pydantic import BaseModel, Field

from supafone_labs.runtime.adapters.base import VoiceProviderAdapter
from supafone_labs.runtime.core.decision import ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import CanonicalEvent
from supafone_labs.runtime.core.policies.consent import ConsentPolicy
from supafone_labs.runtime.core.policies.recovery import RecoveryMessagePolicy
from supafone_labs.runtime.core.policies.scheduling import DateNormalizationPolicy
from supafone_labs.runtime.core.policies.truth import TruthPolicy
from supafone_labs.runtime.core.policies.watchdog import DeadAirWatchdogPolicy
from supafone_labs.runtime.core.state import RuntimeState, apply_events, build_initial_state
from supafone_labs.runtime.workflows.tool_contracts import WorkflowDefinition


class RuntimeConfig(BaseModel):
    workflow_id: str = "generic_support"
    watchdog_delay_seconds: float = 4.0
    provider_defaults: dict[str, str] = Field(default_factory=dict)


class AdheraRuntime:
    def __init__(
        self,
        *,
        workflow: WorkflowDefinition,
        adapters: Iterable[VoiceProviderAdapter],
        config: RuntimeConfig | None = None,
    ) -> None:
        self.workflow = workflow
        self.config = config or RuntimeConfig()
        self.adapters = {adapter.provider_name: adapter for adapter in adapters}
        self.consent_policy = ConsentPolicy()
        self.date_policy = DateNormalizationPolicy()
        self.truth_policy = TruthPolicy()
        self.watchdog_policy = DeadAirWatchdogPolicy(
            delay_seconds=self.config.watchdog_delay_seconds
        )
        self.recovery_policy = RecoveryMessagePolicy()

    def build_state(
        self,
        *,
        provider: str,
        session_id: str,
        provider_session_id: str = "",
    ) -> RuntimeState:
        return build_initial_state(
            provider=provider,
            session_id=session_id,
            provider_session_id=provider_session_id,
            workflow_id=self.workflow.name,
        )

    def get_adapter(self, provider: str) -> VoiceProviderAdapter:
        return self.adapters[provider]

    async def ingest_raw(
        self,
        *,
        provider: str,
        raw_event: dict,
        state: RuntimeState,
    ) -> tuple[RuntimeState, list[CanonicalEvent], list[RuntimeDecision]]:
        adapter = self.get_adapter(provider)
        events = await adapter.parse_event(raw_event)
        next_state = apply_events(events, state)
        decisions = self.evaluate_workflow(next_state, events)
        return next_state, events, decisions

    def apply(self, state: RuntimeState, events: list[CanonicalEvent]) -> RuntimeState:
        return apply_events(events, state)

    def evaluate_workflow(
        self,
        state: RuntimeState,
        events: list[CanonicalEvent],
    ) -> list[RuntimeDecision]:
        decisions: list[RuntimeDecision] = []
        for event in events:
            decisions.extend(self.workflow.on_event(state, event))
        return decisions

    async def compile(
        self,
        *,
        state: RuntimeState,
        decision: RuntimeDecision,
    ) -> list[ProviderAction]:
        adapter = self.get_adapter(state.provider)
        return await adapter.compile(decision, state)

    async def evaluate_watchdog(
        self,
        *,
        state: RuntimeState,
        now: datetime | None = None,
    ) -> tuple[RuntimeDecision | None, list[ProviderAction]]:
        decision = self.watchdog_policy.evaluate(state, now=now)
        if decision is None:
            return None, []
        actions = await self.compile(state=state, decision=decision)
        return decision, actions

    def evaluate_delivery_request(
        self,
        *,
        state: RuntimeState,
        channel: str,
        purpose: str,
    ) -> RuntimeDecision | None:
        return self.consent_policy.evaluate_delivery_request(
            state,
            channel=channel,
            purpose=purpose,
        )

    def normalize_availability_window(
        self,
        raw_text: str,
        *,
        today: date,
    ) -> RuntimeDecision | None:
        return self.date_policy.normalize(raw_text, today=today)

    def reconcile_summary(self, state: RuntimeState, summary: str) -> RuntimeDecision | None:
        return self.truth_policy.reconcile_end_call_summary(state, summary=summary)

    def evaluate_email_repair(self, raw_text: str) -> RuntimeDecision | None:
        return self.recovery_policy.evaluate_email_repair(raw_text)
