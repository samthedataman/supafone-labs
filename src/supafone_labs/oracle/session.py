"""Deprecated session import; use supafone_labs.supervisor.session."""
from supafone_labs.supervisor.session import DirectiveTransform, SupervisorSession

OracleSession = SupervisorSession

__all__ = ["DirectiveTransform", "OracleSession"]
