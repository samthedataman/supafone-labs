from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DecisionKinds:
    INJECT_HIDDEN_INSTRUCTION = "inject_hidden_instruction"
    FORCE_STAGE_TRANSITION = "force_stage_transition"
    REQUEST_AVAILABILITY_WINDOW = "request_availability_window"
    BLOCK_DELIVERY_UNTIL_CONSENT = "block_delivery_until_consent"
    REQUEST_FIELD_REPAIR = "request_field_repair"
    RECONCILE_CALL_SUMMARY = "reconcile_call_summary"


class RuntimeDecision(BaseModel):
    kind: str
    summary: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def inject_hidden_instruction(cls, text: str) -> "RuntimeDecision":
        return cls(
            kind=DecisionKinds.INJECT_HIDDEN_INSTRUCTION,
            summary="Inject a silent operator instruction.",
            payload={"text": text},
        )

    @classmethod
    def force_stage_transition(cls, stage: str) -> "RuntimeDecision":
        return cls(
            kind=DecisionKinds.FORCE_STAGE_TRANSITION,
            summary=f"Move the runtime into the {stage} stage.",
            payload={"stage": stage},
        )

    @classmethod
    def request_availability_window(
        cls,
        raw_text: str,
        normalized_start: str,
        normalized_end: str,
    ) -> "RuntimeDecision":
        return cls(
            kind=DecisionKinds.REQUEST_AVAILABILITY_WINDOW,
            summary="Normalize a relative scheduling window into concrete dates.",
            payload={
                "raw_text": raw_text,
                "normalized_start": normalized_start,
                "normalized_end": normalized_end,
            },
        )

    @classmethod
    def block_delivery_until_consent(cls, channel: str, purpose: str) -> "RuntimeDecision":
        return cls(
            kind=DecisionKinds.BLOCK_DELIVERY_UNTIL_CONSENT,
            summary=f"Block {channel} delivery until consent is recorded.",
            payload={"channel": channel, "purpose": purpose},
        )

    @classmethod
    def request_field_repair(cls, field: str, message: str) -> "RuntimeDecision":
        return cls(
            kind=DecisionKinds.REQUEST_FIELD_REPAIR,
            summary=f"Repair the {field} field before continuing.",
            payload={"field": field, "message": message},
        )

    @classmethod
    def reconcile_call_summary(cls, summary: str, issues: list[str]) -> "RuntimeDecision":
        return cls(
            kind=DecisionKinds.RECONCILE_CALL_SUMMARY,
            summary="Reconcile end-of-call claims against verified state.",
            payload={"summary": summary, "issues": issues},
        )


class ProviderAction(BaseModel):
    provider: str
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)
