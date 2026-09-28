"""Supafone Labs — give any voice agent a supervisor in one line.

The deterministic runtime lives at ``supafone_labs.runtime``; Supafone
Supervisor and the developer-facing facade live here.
"""
from supafone_labs import (
    runtime,  # noqa: F401  (re-export the vendored runtime subpackage)
    stt,  # noqa: F401  (live multilingual transcription subpackage)
)
from supafone_labs.client import (
    OUTBOUND_CALL_MODE_BOUNDS,
    OUTBOUND_CALL_MODE_DEFAULTS,
    OUTBOUND_CALL_MODE_PROVIDER_MATRIX,
    OutboundCallModeCapabilities,
    OutboundCallModeConfig,
    OutboundCallModeObservability,
    OutboundCallModeReadiness,
    Supafone,
    SupafoneError,
    VoicePreview,
    generate_call_stages,
    outbound_call_mode_provider_profile,
    outbound_call_mode_readiness,
)
from supafone_labs.config import (
    SUPERVISOR_MODELS,
    Settings,
    get_settings,
    provider_for_model,
)
from supafone_labs.facade import (
    CRM,
    SCENARIO_PRESETS,
    CallerHistory,
    Feed,
    Knowledge,
    SupafoneLabs,
    SuperchargeResult,
    attach,
    supercharge,
)
from supafone_labs.llm import (
    AnthropicProvider,
    FakeLLMProvider,
    HostedLLMProvider,
    LLMProvider,
    OpenAIProvider,
    build_llm_provider,
    get_default_provider,
    get_provider,
)
from supafone_labs.models import clear_model_cache, discover_supervisor_models
from supafone_labs.supervisor import (
    BeliefStateEngine,
    DirectiveGenerator,
    SupervisorSession,
    SupervisorWorkflow,
    should_emit,
)
from supafone_labs.tiers import Tier, TierError, current_tier, has_feature, require_feature
from supafone_labs.tts import (
    FakeTTSProvider,
    SupafoneLabsTTS,
    TTSProvider,
    available_tts_backends,
    get_default_tts_provider,
    get_tts_provider,
)
from supafone_labs.types import (
    BeliefState,
    Directive,
    DirectiveContract,
    DirectiveKind,
    DirectiveListControl,
    DirectiveTextControl,
    directive_to_decision,
)

from supafone_labs.s2s import (
    GeminiS2S,
    GrokS2S,
    HydraS2S,
    OpenAIS2S,
    S2SProviderName,
    SupafoneS2S,
    UltravoxS2S,
)

__version__ = "0.7.2"

__all__ = [
    "SupafoneS2S",
    "UltravoxS2S",
    "OpenAIS2S",
    "GeminiS2S",
    "GrokS2S",
    "HydraS2S",
    "S2SProviderName",
    # facade
    "supercharge",
    "attach",
    "SupafoneLabs",
    "Feed",
    "CallerHistory",
    "Knowledge",
    "CRM",
    "SuperchargeResult",
    "SCENARIO_PRESETS",
    "Supafone",
    "SupafoneError",
    "VoicePreview",
    "generate_call_stages",
    "OutboundCallModeObservability",
    "OutboundCallModeConfig",
    "OutboundCallModeCapabilities",
    "OutboundCallModeReadiness",
    "OUTBOUND_CALL_MODE_BOUNDS",
    "OUTBOUND_CALL_MODE_DEFAULTS",
    "OUTBOUND_CALL_MODE_PROVIDER_MATRIX",
    "outbound_call_mode_provider_profile",
    "outbound_call_mode_readiness",
    # supervisor
    "SupervisorSession",
    "SupervisorWorkflow",
    "BeliefStateEngine",
    "DirectiveGenerator",
    "should_emit",
    # types
    "BeliefState",
    "Directive",
    "DirectiveContract",
    "DirectiveKind",
    "DirectiveListControl",
    "DirectiveTextControl",
    "directive_to_decision",
    # llm
    "LLMProvider",
    "FakeLLMProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "HostedLLMProvider",
    "get_provider",
    "get_default_provider",
    "build_llm_provider",
    # tiers
    "Tier",
    "TierError",
    "current_tier",
    "has_feature",
    "require_feature",
    # tts
    "TTSProvider",
    "FakeTTSProvider",
    "SupafoneLabsTTS",
    "get_tts_provider",
    "get_default_tts_provider",
    "available_tts_backends",
    # config
    "Settings",
    "get_settings",
    "SUPERVISOR_MODELS",
    "provider_for_model",
    "discover_supervisor_models",
    # Deprecated compatibility exports
    "OracleSession",
    "OracleWorkflow",
    "ORACLE_MODELS",
    "discover_oracle_models",
    "clear_model_cache",
    "runtime",
    "stt",
    "__version__",
]

# Backward-compatible top-level imports. Canonical docs and generated code use
# the Supervisor names.
OracleSession = SupervisorSession
OracleWorkflow = SupervisorWorkflow
ORACLE_MODELS = SUPERVISOR_MODELS
discover_oracle_models = discover_supervisor_models
