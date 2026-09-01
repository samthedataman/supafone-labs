"""Deprecated compatibility imports for the pre-0.6 supervisor namespace."""
from __future__ import annotations

import warnings

from supafone_labs.supervisor import (
    BeliefStateEngine,
    DirectiveGenerator,
    SupervisorSession,
    SupervisorWorkflow,
    should_emit,
)

warnings.warn(
    "supafone_labs.oracle is deprecated; import from supafone_labs.supervisor",
    DeprecationWarning,
    stacklevel=2,
)

OracleSession = SupervisorSession
OracleWorkflow = SupervisorWorkflow

__all__ = [
    "BeliefStateEngine",
    "DirectiveGenerator",
    "OracleSession",
    "OracleWorkflow",
    "should_emit",
]
