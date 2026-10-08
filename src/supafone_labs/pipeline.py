"""Versioned hosted STT × LLM × TTS routing and secret-free configuration."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Mapping
from urllib.parse import quote, urlencode

from supafone_labs.voice import SupafoneVoice

if TYPE_CHECKING:
    from supafone_labs.client import Supafone

LAYERS = ("stt", "llm", "tts")
_IDENTIFIER = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._:/@+-]{0,255}$')
_PROFILE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$')
OPTIONS = {"temperature", "max_tokens", "speed", "stability", "pitch", "style", "endpointing_ms", "region", "deployment", "language", "punctuate", "interim_results"}
_MODES = {"auto", "managed", "byok"}
_SECRET_NAMES = {"apikey", "key", "secret", "token", "password", "authorization", "credentials", "accesskeyid", "secretaccesskey", "privatekey", "clientsecret", "sessiontoken"}


def _secret_free(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).replace("_", "").replace("-", "").lower()
            if normalized in _SECRET_NAMES or any(normalized.endswith(x) for x in ("apikey", "password", "privatekey", "clientsecret", "accesstoken")):
                raise ValueError("Pipeline configuration accepts profile references, never credentials or secrets")
            _secret_free(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _secret_free(item)


def normalize_pipeline(config: Mapping[str, Any]) -> dict[str, Any]:
    """Validate selection structure locally; the server owns model capabilities/readiness."""
    if not isinstance(config, Mapping):
        raise ValueError("pipeline must be an object")
    allowed = {"schema_version", *LAYERS, "credentials", "language", "region", "transport"}
    if set(config) - allowed:
        raise ValueError("Unknown pipeline field")
    version = config.get("schema_version", 1)
    if type(version) is not int or version != 1:
        raise ValueError("pipeline.schema_version must be 1")
    output: dict[str, Any] = {"schema_version": 1}
    for layer in LAYERS:
        item = config.get(layer)
        if not isinstance(item, Mapping):
            raise ValueError(f"pipeline.{layer} must be an object")
        if set(item) - {"provider", "model", "voice", "profile", "options"}:
            raise ValueError(f"Unknown pipeline.{layer} field")
        if not isinstance(item.get("provider"), str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", item["provider"]):
            raise ValueError(f"pipeline.{layer}.provider is invalid")
        if not isinstance(item.get("model"), str) or not _IDENTIFIER.fullmatch(item["model"]):
            raise ValueError(f"pipeline.{layer}.model is invalid")
        for field in ("voice", "profile"):
            if field in item and (not isinstance(item[field], str) or not (_PROFILE if field == "profile" else _IDENTIFIER).fullmatch(item[field])):
                raise ValueError(f"pipeline.{layer}.{field} is invalid")
            if field == "voice" and field in item and layer != "tts":
                raise ValueError("Only the TTS component accepts voice")
        options = item.get("options", {})
        if not isinstance(options, Mapping) or set(options) - OPTIONS:
            raise ValueError(f"pipeline.{layer}.options contains unsupported or sensitive fields")
        if len(json.dumps(options, allow_nan=False)) > 2048 or any(
            not isinstance(v, (str, int, float, bool)) or isinstance(v, str) and len(v) > 256
            for v in options.values()
        ):
            raise ValueError("Component options must be bounded scalar values")
        _secret_free(item)
        output[layer] = deepcopy({k: v for k, v in item.items() if k != "options"})
        if options:
            output[layer]["options"] = deepcopy(dict(options))
    credentials = config.get("credentials", {"default": "auto"})
    if not isinstance(credentials, Mapping) or set(credentials) - {"default", *LAYERS}:
        raise ValueError("credentials must contain only default/stt/llm/tts modes")
    if any(not isinstance(mode, str) or mode not in _MODES for mode in credentials.values()):
        raise ValueError("credential modes must be auto, managed or byok")
    output["credentials"] = {"default": "auto", **credentials}
    for key in ("language", "region", "transport"):
        if key in config:
            if not isinstance(config[key], str) or len(config[key]) > 80 or not re.fullmatch(r"[a-zA-Z0-9_-]+", config[key]):
                raise ValueError(f"pipeline.{key} must be a non-empty string")
            if key == "transport" and config[key] not in {"browser", "phone", "native", "byo_twilio", "byo_telnyx", "byo_plivo", "byo_sip"}:
                raise ValueError("Unsupported pipeline transport")
            output[key] = config[key]
    return output


def validate_voice_selection(data: Mapping[str, Any]) -> None:
    if data.get("pipeline") is not None:
        if data.get("realtime") is not None:
            raise ValueError("pipeline and realtime are mutually exclusive")
        normalize_pipeline(data["pipeline"])


class SupafonePipeline(SupafoneVoice):
    """Compose independently chosen STT, text LLM and TTS in the hosted factory."""

    def __init__(self, client: Supafone, *, stt: Mapping[str, Any],
                 llm: Mapping[str, Any], tts: Mapping[str, Any],
                 credentials: Mapping[str, str] | None = None,
                 schema_version: int = 1, language: str | None = None,
                 region: str | None = None, transport: str | None = None) -> None:
        super().__init__(client)
        config = {"schema_version": schema_version, "stt": stt, "llm": llm, "tts": tts}
        config.update({key: value for key, value in {
            "credentials": credentials, "language": language,
            "region": region, "transport": transport,
        }.items() if value is not None})
        self._pipeline = normalize_pipeline(config)

    @property
    def pipeline(self) -> dict[str, Any]:
        return deepcopy(self._pipeline)

    def _route_payload(self, *, creating: bool = False) -> dict[str, Any]:
        return {"pipeline": self.pipeline, "realtime": None}

    def validate(self, *, context: Mapping[str, Any] | None = None, agency_id: str | None = None) -> Any:
        return self._client.labs.voice.validate(self._route_payload(), context=context, agency_id=agency_id)


class SupafoneRouter:
    """Resolve an explicit route, never silently change providers or payers."""
    def __init__(self, client: Supafone) -> None:
        self._client = client

    def select(self, route: Mapping[str, Any]) -> SupafoneVoice:
        from supafone_labs.s2s import SupafoneS2S, UltravoxS2S

        if not isinstance(route, Mapping):
            raise ValueError("route must be an object")
        kind = route.get("kind")
        if kind == "pipeline":
            if set(route) - {"kind", "pipeline"}:
                raise ValueError("A pipeline route accepts only kind and pipeline")
            return SupafonePipeline(self._client, **normalize_pipeline(route.get("pipeline")))
        if kind in ("s2s", "hybrid"):
            if set(route) - {"kind", "provider", "model", "voice"}:
                raise ValueError("Unknown S2S route field")
            provider = route.get("provider", "ultravox" if kind == "hybrid" else None)
            if kind == "hybrid" and provider != "ultravox":
                raise ValueError("Ultravox is the first supported hybrid route")
            if provider == "ultravox" and not {"model", "voice"}.intersection(route):
                return UltravoxS2S(self._client)
            return SupafoneS2S(self._client, provider=provider, model=route.get("model"), voice=route.get("voice"))
        raise ValueError("route.kind must be hybrid, s2s or pipeline")

    def catalog(self, *, layer: str | None = None) -> Any:
        return self._client.labs.voice.catalog(layer=layer)

    def combinations(self, **kwargs: Any) -> Any:
        return self._client.labs.voice.combinations(**kwargs)

    def validate(self, route: Mapping[str, Any], *, context: Mapping[str, Any] | None = None, agency_id: str | None = None) -> Any:
        return self._client.labs.voice.validate(self.select(route)._route_payload(), context=context, agency_id=agency_id)


class LabsVoiceNamespace:
    """Live catalog, exhaustive combinations, preflight and encrypted profiles."""
    def __init__(self, client: Supafone) -> None:
        self._client = client

    def catalog(self, *, layer: str | None = None) -> Any:
        if layer is not None and layer not in (*LAYERS, "s2s", "hybrid"):
            raise ValueError("layer must be stt, llm, tts, s2s or hybrid")
        query = "?" + urlencode({"layer": layer}) if layer else ""
        return self._client._request_supafone_api("GET", "/api/v1/labs/voice/catalog" + query)

    def combinations(self, *, context: Mapping[str, Any] | None = None,
                     filters: Mapping[str, list[str]] | None = None,
                     offset: int = 0, limit: int = 100, agency_id: str | None = None) -> Any:
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError("offset must be non-negative and limit must be 1–500")
        payload: dict[str, Any] = {"offset": offset, "limit": limit}
        if agency_id is not None:
            payload["agency_id"] = agency_id
        if context is not None:
            payload["context"] = dict(context)
        if filters is not None:
            if set(filters) - set(LAYERS) or any(
                not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values)
                for values in filters.values()
            ):
                raise ValueError("filters must map stt/llm/tts to endpoint ID lists")
            payload["filters"] = deepcopy(dict(filters))
        return self._client._request_supafone_api("POST", "/api/v1/labs/voice/combinations", payload)

    def validate(self, selection: Mapping[str, Any], *, context: Mapping[str, Any] | None = None, agency_id: str | None = None) -> Any:
        if not isinstance(selection, Mapping) or set(selection) - {"pipeline", "realtime"}:
            raise ValueError("selection must contain pipeline or realtime")
        if not selection:
            raise ValueError("selection must contain pipeline or realtime")
        validate_voice_selection(selection)
        payload = deepcopy(dict(selection))
        if agency_id is not None:
            payload["agency_id"] = agency_id
        if payload.get("pipeline") is not None:
            payload["pipeline"] = normalize_pipeline(payload["pipeline"])
        if context is not None:
            payload["context"] = dict(context)
        return self._client._request_supafone_api("POST", "/api/v1/labs/voice/validate", payload)

    @staticmethod
    def _profile_path(provider: str, service: str, profile: str) -> str:
        if service not in LAYERS:
            raise ValueError("service must be stt, llm or tts")
        if any(not isinstance(v, str) or not v.strip() for v in (provider, profile)):
            raise ValueError("provider and profile are required")
        return "/api/v1/labs/voice/profiles/" + "/".join(quote(v, safe="") for v in (provider, service, profile))

    def get_profile(self, provider: str, service: str, *, profile: str = "default", agency_id: str | None = None, mode: str = "auto") -> Any:
        if mode not in _MODES:
            raise ValueError("mode must be auto, managed or byok")
        query = {"mode": mode} if mode != "auto" else {}
        if agency_id is not None:
            query["agency_id"] = agency_id
        suffix = "?" + urlencode(query) if query else ""
        return self._client._request_supafone_api("GET", self._profile_path(provider, service, profile) + suffix)

    def configure_profile(self, provider: str, service: str, *, profile: str = "default",
                          mode: str, credentials: Mapping[str, Any] | None = None, agency_id: str | None = None) -> Any:
        if mode not in {"managed", "byok"}:
            raise ValueError("profile mode must be managed or byok")
        if mode == "managed" and credentials:
            raise ValueError("managed mode does not accept customer credentials")
        if mode == "byok" and not credentials:
            raise ValueError("byok requires credentials")
        return self._client._request_supafone_api("PUT", self._profile_path(provider, service, profile),
            {"mode": mode, "credentials": deepcopy(dict(credentials or {})), **({"agency_id": agency_id} if agency_id is not None else {})})

    getProfile = get_profile
    configureProfile = configure_profile


def voice_catalog_snapshot() -> dict[str, Any]:
    """Bundled discovery snapshot; never a substitute for live readiness checks."""
    from importlib.resources import files
    return json.loads(files("supafone_labs").joinpath("voice_catalog.json").read_text())


def pipeline_schema() -> dict[str, Any]:
    """Machine-readable, secret-free pipeline selection shape."""
    from importlib.resources import files
    return json.loads(files("supafone_labs").joinpath("pipeline.schema.json").read_text())
