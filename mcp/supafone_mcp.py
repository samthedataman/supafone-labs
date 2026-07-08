#!/usr/bin/env python3
"""Dependency-light Supafone Labs MCP server for Claude Desktop.

This implements the MCP stdio JSON-RPC surface directly so it can run in a local
Claude Desktop config without installing an MCP framework. It intentionally keeps
all writes out of stdout except JSON-RPC messages.
"""
from __future__ import annotations

import json
import os
import base64
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Optional
from urllib import error, parse, request


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from supafone_labs import Supafone, SupafoneError, generate_call_stages
except Exception:  # pragma: no cover - exercised only when SDK import is broken.
    Supafone = None  # type: ignore[assignment]
    SupafoneError = RuntimeError  # type: ignore[assignment]
    generate_call_stages = None  # type: ignore[assignment]


SERVER_NAME = "supafone-labs-mcp"
SERVER_VERSION = "0.1.0"
DEFAULT_PROTOCOL_VERSION = "2024-11-05"
DEFAULT_HOSTED_API_BASE = "https://api.supafone.ai"
DEFAULT_LABS_API_BASE = "https://api.labs.supafone.ai"

AUTH_ARG_KEYS = {
    "apiKey",
    "api_key",
    "supafoneApiKey",
    "supafone_api_key",
    "labsApiKey",
    "labs_api_key",
    "supafoneApiBaseUrl",
    "supafone_api_base_url",
    "supafoneBaseUrl",
    "supafone_base_url",
    "labsApiBaseUrl",
    "labs_api_base_url",
    "labsBaseUrl",
    "labs_base_url",
}


class ToolError(RuntimeError):
    """Error reported as an MCP tool result instead of a JSON-RPC protocol error."""


def _json_dumps(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)


def _pick(data: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def _env(*keys: str) -> Optional[str]:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None


def _merge_config(arguments: Mapping[str, Any]) -> dict[str, Any]:
    config = arguments.get("config")
    if config is None:
        merged: dict[str, Any] = {}
    elif isinstance(config, Mapping):
        merged = dict(config)
    else:
        raise ToolError("config must be an object when provided")

    for key, value in arguments.items():
        if key == "config" or key in AUTH_ARG_KEYS or value is None:
            continue
        merged[key] = value
    return merged


def _safe_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _safe_float(value: Any, *, default: float, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _log_key(log: Mapping[str, Any]) -> str:
    return "|".join(
        str(log.get(name, ""))
        for name in ("at", "endpoint", "duration_ms", "seconds_billed", "detail")
    )


def _agent_schema(*, with_number: bool = False) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "config": {
            "type": "object",
            "description": "Full Supafone hosted-agent config. Top-level fields override this object.",
            "additionalProperties": True,
        },
        "agentKey": {"type": "string", "description": "Stable slug for the agent."},
        "name": {"type": "string", "description": "Human-readable agent name."},
        "assistantName": {"type": "string", "description": "Caller-facing assistant name."},
        "businessName": {"type": "string"},
        "industry": {"type": "string"},
        "websiteUrl": {"type": "string"},
        "goal": {"type": "string"},
        "greeting": {"type": "string"},
        "systemPrompt": {"type": "string"},
        "language": {"type": "string"},
        "voice": {
            "type": "object",
            "additionalProperties": True,
            "description": "Voice config, for example {provider, voiceId, model}.",
        },
        "labs": {
            "type": "object",
            "additionalProperties": True,
            "description": "Self-healing watcher config. Use enabled:true only when Labs should run.",
        },
        "providerKeys": {
            "type": "object",
            "additionalProperties": True,
            "description": "Optional BYOK provider credentials forwarded to the API.",
        },
        "byok": {
            "type": "object",
            "additionalProperties": True,
            "description": "Alias for provider-specific BYOK credentials.",
        },
        "telephony": {
            "type": "object",
            "additionalProperties": True,
            "description": "Telephony mode/provider/credentials.",
        },
        "tools": {"type": "object", "additionalProperties": True},
        "metadata": {"type": "object", "additionalProperties": True},
        "apiKey": {
            "type": "string",
            "description": "Optional per-call hosted API key override. Prefer SUPAFONE_API_KEY env.",
        },
        "supafoneApiBaseUrl": {
            "type": "string",
            "description": "Optional hosted API base URL override.",
        },
    }
    if with_number:
        properties["number"] = {
            "type": "object",
            "additionalProperties": True,
            "description": "Number search/provision config, for example {search:{areaCode:'415'}}.",
        }
    return {"type": "object", "properties": properties, "additionalProperties": True}


def _logs_schema(*, polling: bool = False) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 500,
            "default": 100,
            "description": "Maximum log rows to request from the Labs API.",
        },
        "apiKey": {
            "type": "string",
            "description": "Optional per-call Labs API key override. Prefer SUPAFONE_LABS_API_KEY env.",
        },
        "labsApiBaseUrl": {
            "type": "string",
            "description": "Optional Labs Cloud API base URL override.",
        },
    }
    if polling:
        properties.update(
            {
                "iterations": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 60,
                    "default": 3,
                    "description": "How many bounded polling rounds to run.",
                },
                "intervalSeconds": {
                    "type": "number",
                    "minimum": 0.5,
                    "maximum": 10,
                    "default": 2,
                    "description": "Delay between polling rounds.",
                },
            }
        )
    return {"type": "object", "properties": properties, "additionalProperties": False}


def _phone_number_lifecycle_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "numberId": {"type": "string", "description": "Supafone number id."},
            "number_id": {"type": "string", "description": "Supafone number id."},
            "agencyId": {"type": "string"},
            "agency_id": {"type": "string"},
            "reason": {"type": "string"},
            "metadata": {"type": "object", "additionalProperties": True},
            "apiKey": {"type": "string", "description": "Optional hosted API key override."},
            "supafoneApiBaseUrl": {"type": "string", "description": "Optional hosted API base URL."},
        },
        "additionalProperties": True,
    }


def _voice_preview_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "voice": {"type": "string", "default": "supafone-labs-calm-en"},
            "text": {
                "type": "string",
                "default": "Hi, this is your Supafone agent voice preview.",
            },
            "apiKey": {"type": "string", "description": "Optional Labs API key override."},
            "labsApiBaseUrl": {"type": "string", "description": "Optional Labs API base URL."},
        },
        "additionalProperties": False,
    }


def _artifact_list_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "agentKey": {"type": "string"},
            "agent_key": {"type": "string"},
            "callId": {"type": "string"},
            "call_id": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 100},
            "apiKey": {"type": "string"},
            "supafoneApiBaseUrl": {"type": "string"},
        },
        "additionalProperties": True,
    }


TOOLS: list[dict[str, Any]] = [
    {
        "name": "create_inbound_agent",
        "description": "Create a hosted inbound Supafone voice agent using the Python SDK.",
        "inputSchema": _agent_schema(),
    },
    {
        "name": "create_outbound_agent",
        "description": "Create a hosted outbound Supafone voice agent using the Python SDK.",
        "inputSchema": _agent_schema(),
    },
    {
        "name": "create_inbound_agent_with_number",
        "description": "Create an inbound agent and provision or assign a phone number.",
        "inputSchema": _agent_schema(with_number=True),
    },
    {
        "name": "create_outbound_agent_with_number",
        "description": "Create an outbound agent and provision or assign a phone number.",
        "inputSchema": _agent_schema(with_number=True),
    },
    {
        "name": "generate_call_stages",
        "description": "Generate default Supafone call stages from prompt, goal, business metadata, and direction.",
        "inputSchema": _agent_schema(),
    },
    {
        "name": "delete_agent",
        "description": "Delete a hosted Supafone agent. Optionally release assigned numbers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agentKey": {"type": "string"},
                "agent_key": {"type": "string"},
                "releaseNumbers": {"type": "boolean"},
                "release_numbers": {"type": "boolean"},
                "apiKey": {"type": "string"},
                "supafoneApiBaseUrl": {"type": "string"},
            },
            "additionalProperties": True,
        },
    },
    {
        "name": "get_usage",
        "description": "Fetch today's Supafone Labs usage/caps for the configured Labs key.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "apiKey": {
                    "type": "string",
                    "description": "Optional per-call Labs API key override.",
                },
                "labsApiBaseUrl": {
                    "type": "string",
                    "description": "Optional Labs Cloud API base URL override.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "list_phone_numbers",
        "description": "List Supafone-managed phone numbers in the hosted account.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agencyId": {"type": "string"},
                "activeOnly": {"type": "boolean"},
                "apiKey": {"type": "string"},
                "supafoneApiBaseUrl": {"type": "string"},
            },
            "additionalProperties": True,
        },
    },
    {
        "name": "search_phone_numbers",
        "description": "Search Supafone-managed phone number inventory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "config": {"type": "object", "additionalProperties": True},
                "areaCode": {"type": "string"},
                "countryCode": {"type": "string"},
                "numberStrategy": {"type": "string"},
                "apiKey": {"type": "string"},
                "supafoneApiBaseUrl": {"type": "string"},
            },
            "additionalProperties": True,
        },
    },
    {
        "name": "unassign_phone_number",
        "description": "Detach a phone number from an agent but keep it reserved.",
        "inputSchema": _phone_number_lifecycle_schema(),
    },
    {
        "name": "release_phone_number",
        "description": "Release a phone number reservation, usually returning it to the pool.",
        "inputSchema": _phone_number_lifecycle_schema(),
    },
    {
        "name": "return_phone_number_to_pool",
        "description": "Explicit alias for releasing a number back to the shared pool.",
        "inputSchema": _phone_number_lifecycle_schema(),
    },
    {
        "name": "delete_phone_number",
        "description": "Delete/release a phone-number reservation when backend policy allows it.",
        "inputSchema": _phone_number_lifecycle_schema(),
    },
    {
        "name": "list_logs",
        "description": "List recent Supafone Labs audit logs for whispers, TTS, STT, QA, and calls.",
        "inputSchema": _logs_schema(),
    },
    {
        "name": "list_calls",
        "description": "List recent hosted-agent calls/call artifacts for a Supafone account.",
        "inputSchema": _artifact_list_schema(),
    },
    {
        "name": "list_recordings",
        "description": "List hosted-agent call recordings.",
        "inputSchema": _artifact_list_schema(),
    },
    {
        "name": "delete_recording",
        "description": "Delete a hosted-agent recording where backend policy permits it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recordingId": {"type": "string"},
                "recording_id": {"type": "string"},
                "reason": {"type": "string"},
                "apiKey": {"type": "string"},
                "supafoneApiBaseUrl": {"type": "string"},
            },
            "additionalProperties": True,
        },
    },
    {
        "name": "list_transcripts",
        "description": "List hosted-agent call transcripts.",
        "inputSchema": _artifact_list_schema(),
    },
    {
        "name": "tail_logs",
        "description": "Poll Supafone Labs logs for a short bounded stream of new entries.",
        "inputSchema": _logs_schema(polling=True),
    },
    {
        "name": "poll_logs",
        "description": "Alias of tail_logs for agents that ask to poll logs explicitly.",
        "inputSchema": _logs_schema(polling=True),
    },
    {
        "name": "list_voices",
        "description": "List the full Supafone Labs voice catalog with configured/live provider flags.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "apiKey": {"type": "string"},
                "labsApiBaseUrl": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "preview_voice",
        "description": "Render a short voice preview. Returns base64 audio plus media type.",
        "inputSchema": _voice_preview_schema(),
    },
]


class SupafoneMCPServer:
    def __init__(self, *, sleep: Callable[[float], None] = time.sleep) -> None:
        self._sleep = sleep

    def handle(self, message: Mapping[str, Any]) -> Optional[dict[str, Any]]:
        message_id = message.get("id")
        method = message.get("method")
        if method is None:
            return self._error(message_id, -32600, "Missing JSON-RPC method")

        if str(method).startswith("notifications/"):
            return None

        try:
            if method == "initialize":
                return self._result(message_id, self._initialize(message.get("params") or {}))
            if method == "ping":
                return self._result(message_id, {})
            if method == "tools/list":
                return self._result(message_id, {"tools": TOOLS})
            if method == "tools/call":
                return self._result(message_id, self._tools_call(message.get("params") or {}))
            if method in {"resources/list", "prompts/list"}:
                key = "resources" if method == "resources/list" else "prompts"
                return self._result(message_id, {key: []})
            return self._error(message_id, -32601, f"Unknown method: {method}")
        except Exception as exc:  # pragma: no cover - defensive protocol guard.
            return self._error(message_id, -32603, str(exc))

    def _initialize(self, params: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "protocolVersion": params.get("protocolVersion") or DEFAULT_PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        }

    def _tools_call(self, params: Mapping[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            return self._tool_error("tools/call requires a string name")
        if not isinstance(arguments, Mapping):
            return self._tool_error("tools/call arguments must be an object")

        try:
            result = self.call_tool(name, arguments)
            return self._tool_result(result)
        except ToolError as exc:
            return self._tool_error(str(exc))
        except SupafoneError as exc:
            body = getattr(exc, "body", None)
            status = getattr(exc, "status", None)
            detail = {"message": str(exc), "status": status, "body": body}
            return self._tool_error(_json_dumps(detail))
        except Exception as exc:  # pragma: no cover - defensive tool guard.
            return self._tool_error(f"{type(exc).__name__}: {exc}")

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Any:
        if name == "create_inbound_agent":
            return self._hosted_client(arguments).labs.agents.create_inbound(
                _merge_config(arguments)
            )
        if name == "create_outbound_agent":
            return self._hosted_client(arguments).labs.agents.create_outbound(
                _merge_config(arguments)
            )
        if name == "create_inbound_agent_with_number":
            return self._hosted_client(arguments).labs.agents.create_inbound_with_number(
                _merge_config(arguments)
            )
        if name == "create_outbound_agent_with_number":
            return self._hosted_client(arguments).labs.agents.create_outbound_with_number(
                _merge_config(arguments)
            )
        if name == "generate_call_stages":
            if generate_call_stages is None:
                raise ToolError("supafone_labs SDK import failed; run from the repo or install supafone-labs")
            return {"call_stages": generate_call_stages(_merge_config(arguments))}
        if name == "delete_agent":
            agent_key = _pick(arguments, "agentKey", "agent_key")
            if not agent_key:
                raise ToolError("agentKey is required")
            return self._hosted_client(arguments).labs.agents.delete(
                str(agent_key),
                releaseNumbers=_pick(arguments, "releaseNumbers", "release_numbers"),
            )
        if name == "get_usage":
            return self._labs_get("/v1/usage", arguments)
        if name == "list_phone_numbers":
            return self._hosted_client(arguments).labs.phone_numbers.list(
                agencyId=_pick(arguments, "agencyId", "agency_id"),
                activeOnly=_pick(arguments, "activeOnly", "active_only"),
            )
        if name == "search_phone_numbers":
            return self._hosted_client(arguments).labs.phone_numbers.search(_merge_config(arguments))
        if name == "unassign_phone_number":
            return self._hosted_client(arguments).labs.phone_numbers.unassign(
                self._number_id(arguments), _merge_config(arguments)
            )
        if name == "release_phone_number":
            return self._hosted_client(arguments).labs.phone_numbers.release(
                self._number_id(arguments), _merge_config(arguments)
            )
        if name == "return_phone_number_to_pool":
            return self._hosted_client(arguments).labs.phone_numbers.return_to_pool(
                self._number_id(arguments), _merge_config(arguments)
            )
        if name == "delete_phone_number":
            return self._hosted_client(arguments).labs.phone_numbers.delete(
                self._number_id(arguments), _merge_config(arguments)
            )
        if name == "list_logs":
            limit = _safe_int(arguments.get("limit"), default=100, minimum=1, maximum=500)
            return self._labs_get(f"/v1/logs?{parse.urlencode({'limit': limit})}", arguments)
        if name in {"tail_logs", "poll_logs"}:
            return self._poll_logs(arguments)
        if name == "list_calls":
            return self._hosted_client(arguments).labs.calls.list(
                agentKey=_pick(arguments, "agentKey", "agent_key"),
                limit=arguments.get("limit"),
            )
        if name == "list_recordings":
            return self._hosted_client(arguments).labs.recordings.list(
                agentKey=_pick(arguments, "agentKey", "agent_key"),
                callId=_pick(arguments, "callId", "call_id"),
                limit=arguments.get("limit"),
            )
        if name == "delete_recording":
            recording_id = _pick(arguments, "recordingId", "recording_id")
            if not recording_id:
                raise ToolError("recordingId is required")
            return self._hosted_client(arguments).labs.recordings.delete(
                str(recording_id),
                reason=arguments.get("reason"),
            )
        if name == "list_transcripts":
            return self._hosted_client(arguments).labs.transcripts.list(
                agentKey=_pick(arguments, "agentKey", "agent_key"),
                callId=_pick(arguments, "callId", "call_id"),
                limit=arguments.get("limit"),
            )
        if name == "list_voices":
            return self._labs_get("/v1/voices", arguments)
        if name == "preview_voice":
            voice = str(arguments.get("voice") or "supafone-labs-calm-en")
            text = str(arguments.get("text") or "Hi, this is your Supafone agent voice preview.")
            audio, media_type = self._labs_bytes("/v1/tts", {"voice": voice, "text": text}, arguments)
            return {
                "voice": voice,
                "media_type": media_type,
                "audio_base64": base64.b64encode(audio).decode("ascii"),
            }
        raise ToolError(f"Unknown tool: {name}")

    def _number_id(self, arguments: Mapping[str, Any]) -> str:
        number_id = _pick(arguments, "numberId", "number_id")
        if not number_id:
            raise ToolError("numberId is required")
        return str(number_id)

    def _hosted_client(self, arguments: Mapping[str, Any]) -> Any:
        if Supafone is None:
            raise ToolError("supafone_labs SDK import failed; run from the repo or install supafone-labs")

        api_key = (
            _pick(arguments, "apiKey", "api_key", "supafoneApiKey", "supafone_api_key")
            or _env("SUPAFONE_API_KEY", "SUPAFONE_LABS_API_KEY")
        )
        if not api_key:
            raise ToolError("Set SUPAFONE_API_KEY or pass apiKey to create hosted agents")

        base_url = (
            _pick(
                arguments,
                "supafoneApiBaseUrl",
                "supafone_api_base_url",
                "supafoneBaseUrl",
                "supafone_base_url",
            )
            or _env("SUPAFONE_API_BASE_URL", "SUPAFONE_BASE_URL")
            or DEFAULT_HOSTED_API_BASE
        )
        return Supafone(api_key=str(api_key), supafone_api_base_url=str(base_url))

    def _labs_get(self, path: str, arguments: Mapping[str, Any]) -> Any:
        return self._http_json("GET", self._labs_url(path, arguments), None, self._labs_key(arguments))

    def _labs_bytes(
        self,
        path: str,
        payload: dict[str, Any],
        arguments: Mapping[str, Any],
    ) -> tuple[bytes, str]:
        return self._http_bytes("POST", self._labs_url(path, arguments), payload, self._labs_key(arguments))

    def _poll_logs(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        limit = _safe_int(arguments.get("limit"), default=100, minimum=1, maximum=500)
        iterations = _safe_int(arguments.get("iterations"), default=3, minimum=1, maximum=60)
        interval = _safe_float(
            _pick(arguments, "intervalSeconds", "interval_seconds"),
            default=2.0,
            minimum=0.5,
            maximum=10.0,
        )

        batches: list[dict[str, Any]] = []
        seen: set[str] = set()
        latest_first: list[dict[str, Any]] = []
        for index in range(iterations):
            payload = self._labs_get(
                f"/v1/logs?{parse.urlencode({'limit': limit})}",
                arguments,
            )
            rows = payload.get("logs", []) if isinstance(payload, Mapping) else []
            new_rows = []
            for row in rows:
                if not isinstance(row, Mapping):
                    continue
                key = _log_key(row)
                if key in seen:
                    continue
                seen.add(key)
                new_rows.append(dict(row))
            latest_first = [dict(row) for row in rows if isinstance(row, Mapping)]
            batches.append({"iteration": index + 1, "new_logs": new_rows})
            if index < iterations - 1:
                self._sleep(interval)
        return {
            "polling": {
                "iterations": iterations,
                "interval_seconds": interval,
                "limit": limit,
            },
            "batches": batches,
            "latest_logs": latest_first,
        }

    def _labs_key(self, arguments: Mapping[str, Any]) -> str:
        api_key = (
            _pick(arguments, "apiKey", "api_key", "labsApiKey", "labs_api_key")
            or _env("SUPAFONE_LABS_API_KEY", "SUPAFONE_API_KEY")
        )
        if not api_key:
            raise ToolError("Set SUPAFONE_LABS_API_KEY or pass apiKey to read usage/logs")
        return str(api_key)

    def _labs_url(self, path: str, arguments: Mapping[str, Any]) -> str:
        base_url = (
            _pick(arguments, "labsApiBaseUrl", "labs_api_base_url", "labsBaseUrl", "labs_base_url")
            or _env("SUPAFONE_LABS_API_BASE_URL", "SUPAFONE_LABS_BASE_URL")
            or DEFAULT_LABS_API_BASE
        )
        return str(base_url).rstrip("/") + path

    def _http_json(
        self,
        method: str,
        url: str,
        payload: Optional[dict[str, Any]],
        api_key: str,
    ) -> Any:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"

        req = request.Request(url, data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed: Any = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
            raise ToolError(_json_dumps({"status": exc.code, "body": parsed})) from exc
        except error.URLError as exc:
            raise ToolError(f"Network error calling {url}: {exc.reason}") from exc

    def _http_bytes(
        self,
        method: str,
        url: str,
        payload: Optional[dict[str, Any]],
        api_key: str,
    ) -> tuple[bytes, str]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Authorization": f"Bearer {api_key}", "Accept": "audio/*"}
        if payload is not None:
            headers["Content-Type"] = "application/json"

        req = request.Request(url, data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=30) as resp:
                return resp.read(), resp.headers.get("content-type") or "application/octet-stream"
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed: Any = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
            raise ToolError(_json_dumps({"status": exc.code, "body": parsed})) from exc
        except error.URLError as exc:
            raise ToolError(f"Network error calling {url}: {exc.reason}") from exc

    def _tool_result(self, result: Any) -> dict[str, Any]:
        text = result if isinstance(result, str) else _json_dumps(result)
        response: dict[str, Any] = {"content": [{"type": "text", "text": text}], "isError": False}
        if isinstance(result, (dict, list)):
            response["structuredContent"] = result
        return response

    def _tool_error(self, message: str) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": message}], "isError": True}

    def _result(self, message_id: Any, result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": message_id, "result": result}

    def _error(self, message_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def serve() -> int:
    server = SupafoneMCPServer()
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
        else:
            if not isinstance(message, Mapping):
                response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32600, "message": "JSON-RPC message must be an object"},
                }
            else:
                response = server.handle(message)
        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":"), ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(serve())
