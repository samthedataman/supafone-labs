"""Supafone Labs — give any voice agent a second mind in one line.

The deterministic, provider-agnostic runtime lives at ``supafone_labs.runtime``; the LLM
oracle and the developer-facing facade live here.
"""
from supafone_labs import runtime  # noqa: F401  (re-export the vendored runtime subpackage)
from supafone_labs.config import ORACLE_MODELS, Settings, get_settings, provider_for_model
from supafone_labs.client import Supafone, SupafoneError, VoicePreview, generate_call_stages
from supafone_labs.models import clear_model_cache, discover_oracle_models
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
from supafone_labs.oracle import (
    BeliefStateEngine,
    DirectiveGenerator,
    OracleSession,
    OracleWorkflow,
    should_emit,
)
from supafone_labs import stt  # noqa: F401  (live multilingual transcription subpackage)
from supafone_labs.tiers import Tier, TierError, current_tier, has_feature, require_feature
from supafone_labs.tts import (
    FakeTTSProvider,
    SupafoneLabsTTS,
    TTSProvider,
    available_tts_backends,
    get_default_tts_provider,
    get_tts_provider,
)
from supafone_labs.types import BeliefState, Directive, DirectiveKind, directive_to_decision

__version__ = "0.3.1"

__all__ = [
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
    # oracle
    "OracleSession",
    "OracleWorkflow",
    "BeliefStateEngine",
    "DirectiveGenerator",
    "should_emit",
    # types
    "BeliefState",
    "Directive",
    "DirectiveKind",
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
    "ORACLE_MODELS",
    "provider_for_model",
    "discover_oracle_models",
    "clear_model_cache",
    "runtime",
    "stt",
    "__version__",
]
