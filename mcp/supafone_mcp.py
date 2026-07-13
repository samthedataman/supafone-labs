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
SERVER_VERSION = "0.3.0"
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
    # Main-app (app.supafone.ai account) auth for campaign/call tools.
    "token",
    "accessToken",
    "access_token",
    "email",
    "password",
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


def _sl_token_env() -> Optional[str]:
    """One-key auth fallback: SUPAFONE_TOKEN holding an `sl_` Labs key doubles
    as the Labs API key, so one env var covers the labs AND product lanes."""
    token = _env("SUPAFONE_TOKEN", "SUPAFONE_ACCESS_TOKEN", "SUPAFONE_JWT")
    return token if token and token.startswith("sl_") else None


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


# ---------------------------------------------------------------------------
# Main-app tools (campaigns + real outbound calls) — these hit the Supafone
# product API (api.supafone.ai /api/v1/*), authenticated with the SAME account
# login as app.supafone.ai: pass `token` (a JWT, or an `sl_` Labs API key —
# one-key auth), or set SUPAFONE_TOKEN, or set SUPAFONE_EMAIL +
# SUPAFONE_PASSWORD and the server logs in for you (and re-logs-in
# transparently when the token expires).
# ---------------------------------------------------------------------------

_MAIN_AUTH_PROPS: dict[str, Any] = {
    "token": {
        "type": "string",
        "description": "Supafone account JWT or sl_ Labs API key (one key works on both APIs). Prefer SUPAFONE_TOKEN env.",
    },
    "email": {
        "type": "string",
        "description": "Account email — used with password to log in when no token is set. Prefer SUPAFONE_EMAIL env.",
    },
    "password": {
        "type": "string",
        "description": "Account password for login. Prefer SUPAFONE_PASSWORD env.",
    },
    "supafoneApiBaseUrl": {
        "type": "string",
        "description": "Optional API base URL override (default https://api.supafone.ai).",
    },
}


def _main_schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {**properties, **_MAIN_AUTH_PROPS},
        "additionalProperties": True,
    }
    if required:
        schema["required"] = required
    return schema


_CAMPAIGN_ID_PROPS: dict[str, Any] = {
    "campaignId": {"type": "string", "description": "Campaign id."},
    "campaign_id": {"type": "string", "description": "Campaign id."},
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
        "name": "get_tester_capabilities",
        "description": "Check whether the managed provider-neutral phone grader is ready and list its scenarios.",
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
        "name": "test_phone_agent",
        "description": (
            "PLACE A REAL TEST CALL to any authorized E.164 voice-agent number. The synthetic "
            "caller works across Vapi, Retell, Bland, OpenAI Realtime, Grok, LiveKit, custom "
            "runtimes, Twilio, Telnyx, SIP, and other target stacks because PSTN is the boundary. "
            "Burns tester credits and requires authorized=true."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "toNumber": {"type": "string", "description": "Authorized target in E.164, e.g. +14155550100."},
                "to_number": {"type": "string"},
                "scenario": {
                    "type": "string",
                    "enum": ["price_probe", "false_booking", "language_switch", "distressed"],
                },
                "agentLabel": {"type": "string"},
                "agent_label": {"type": "string"},
                "aiProvider": {"type": "string", "description": "Target runtime metadata."},
                "ai_provider": {"type": "string"},
                "telephonyProvider": {"type": "string", "description": "Target carrier metadata."},
                "telephony_provider": {"type": "string"},
                "authorized": {
                    "type": "boolean",
                    "description": "Must be true: caller owns or has permission to test the target.",
                },
                "apiKey": {"type": "string"},
                "labsApiBaseUrl": {"type": "string"},
            },
            "required": ["authorized"],
            "additionalProperties": True,
        },
    },
    {
        "name": "get_phone_test",
        "description": "Read carrier state, live transcript, and verdict for a provider-neutral phone-test session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sessionId": {"type": "string"},
                "session_id": {"type": "string"},
                "apiKey": {"type": "string"},
                "labsApiBaseUrl": {"type": "string"},
            },
            "additionalProperties": True,
        },
    },
    {
        "name": "wait_for_phone_test",
        "description": "Poll a real phone test until it returns a final transcript/verdict or the bounded timeout expires.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sessionId": {"type": "string"},
                "session_id": {"type": "string"},
                "pollSeconds": {"type": "number", "minimum": 0.5, "maximum": 10},
                "timeoutSeconds": {"type": "number", "minimum": 1, "maximum": 240},
                "apiKey": {"type": "string"},
                "labsApiBaseUrl": {"type": "string"},
            },
            "additionalProperties": True,
        },
    },
    {
        "name": "generate_qa_scenarios",
        "description": "Generate adversarial QA scenarios from a voice agent prompt without placing a phone call.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agentPrompt": {"type": "string"},
                "agent_prompt": {"type": "string"},
                "count": {"type": "integer", "minimum": 1, "maximum": 12},
                "apiKey": {"type": "string"},
                "labsApiBaseUrl": {"type": "string"},
            },
            "additionalProperties": True,
        },
    },
    {
        "name": "list_qa_runs",
        "description": "List prior Supafone QA and Watcher benchmark runs for an agent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                "apiKey": {"type": "string"},
                "labsApiBaseUrl": {"type": "string"},
            },
            "additionalProperties": True,
        },
    },
    {
        "name": "run_watcher_qa",
        "description": (
            "Run the A/B Watcher benchmark: every selected scenario runs once without and once "
            "with supervision. Requires Labs email/password session auth and uses oracle credits."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scenarios": {"type": "array", "items": {"type": "string"}},
                "turns": {"type": "integer", "minimum": 1, "maximum": 8},
                "email": {"type": "string"},
                "password": {"type": "string"},
                "apiKey": {"type": "string"},
                "labsApiBaseUrl": {"type": "string"},
            },
            "additionalProperties": True,
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
    # --- main-app: campaigns + real calls (Supafone account login) ----------
    {
        "name": "list_voice_agents",
        "description": "List the Supafone account's voice agents (id, name, phone number) — pick an agent_id for campaigns and calls.",
        "inputSchema": _main_schema({}),
    },
    {
        "name": "place_call",
        "description": (
            "PLACE A REAL OUTBOUND PHONE CALL: dials toNumber from the account's calling "
            "provider and bridges the given Supafone voice agent onto the line. Burns call "
            "credits and rings a real phone — use deliberately."
        ),
        "inputSchema": _main_schema(
            {
                "agentId": {"type": "string", "description": "Voice agent to put on the call."},
                "agent_id": {"type": "string"},
                "toNumber": {"type": "string", "description": "E.164 destination, e.g. +15551234567."},
                "to_number": {"type": "string"},
            },
        ),
    },
    {
        "name": "list_campaigns",
        "description": "List outbound campaigns on the Supafone account, with live stats per campaign.",
        "inputSchema": _main_schema(
            {"accountId": {"type": "string"}, "account_id": {"type": "string"}},
        ),
    },
    {
        "name": "create_campaign",
        "description": "Create a new outbound campaign (draft). Goals: book | qualify | follow_up | reengage.",
        "inputSchema": _main_schema(
            {
                "name": {"type": "string", "description": "Campaign name."},
                "goal": {"type": "string", "description": "book | qualify | follow_up | reengage."},
                "agentId": {"type": "string", "description": "Voice agent for the campaign's calls."},
                "agent_id": {"type": "string"},
                "accountId": {"type": "string"},
                "account_id": {"type": "string"},
            },
        ),
    },
    {
        "name": "get_campaign",
        "description": "Fetch one campaign (config, settings, cadence) with live stats.",
        "inputSchema": _main_schema(dict(_CAMPAIGN_ID_PROPS)),
    },
    {
        "name": "update_campaign",
        "description": (
            "Update a campaign: name, goal, agentId, emailSubject, emailBody, cadence "
            "([{channel:'voice'|'email', delay_hours}]), or settings (merged server-side — e.g. "
            "qualification_criteria, outbound_prompts, native_signing, caller_id_number)."
        ),
        "inputSchema": _main_schema(
            {
                **_CAMPAIGN_ID_PROPS,
                "name": {"type": "string"},
                "goal": {"type": "string"},
                "agentId": {"type": "string"},
                "agent_id": {"type": "string"},
                "emailSubject": {"type": "string"},
                "email_subject": {"type": "string"},
                "emailBody": {"type": "string"},
                "email_body": {"type": "string"},
                "cadence": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                "settings": {"type": "object", "additionalProperties": True},
            },
        ),
    },
    {
        "name": "add_campaign_recipients",
        "description": (
            "Add leads to a campaign. Each recipient: {name, phone, email, outreach_consent:'yes', "
            "...extra fields}. Consent is required before any voice/email touch."
        ),
        "inputSchema": _main_schema(
            {
                **_CAMPAIGN_ID_PROPS,
                "recipients": {
                    "type": "array",
                    "items": {"type": "object", "additionalProperties": True},
                    "description": "Lead rows to add.",
                },
            },
        ),
    },
    {
        "name": "list_campaign_recipients",
        "description": "List a campaign's recipients with their cadence state (queued, in_progress, booked, signed…).",
        "inputSchema": _main_schema(dict(_CAMPAIGN_ID_PROPS)),
    },
    {
        "name": "launch_campaign",
        "description": (
            "LAUNCH a campaign: schedules every consented recipient and starts REAL calls/emails "
            "on the cadence immediately. Use deliberately."
        ),
        "inputSchema": _main_schema(dict(_CAMPAIGN_ID_PROPS)),
    },
    {
        "name": "pause_campaign",
        "description": "Pause an active campaign — no further dials or emails until relaunched.",
        "inputSchema": _main_schema(dict(_CAMPAIGN_ID_PROPS)),
    },
    {
        "name": "list_campaign_presets",
        "description": "List campaign presets: the built-in playbooks plus the account's saved custom presets.",
        "inputSchema": _main_schema({}),
    },
    {
        "name": "apply_campaign_preset",
        "description": (
            "Apply a preset (built-in id like 'appointment_setting', or a custom_… id) to a campaign "
            "in one atomic write: goal, qualification questions, scripts, and — for custom presets — "
            "email copy and the signing document."
        ),
        "inputSchema": _main_schema(
            {
                **_CAMPAIGN_ID_PROPS,
                "presetId": {"type": "string", "description": "Preset id to apply."},
                "preset_id": {"type": "string"},
            },
        ),
    },
    {
        "name": "create_sign_link",
        "description": (
            "Mint a recipient's tracked tap-to-sign link (/w/m/{token}). Inherits the campaign's "
            "uploaded signing document automatically when one is configured."
        ),
        "inputSchema": _main_schema(
            {
                **_CAMPAIGN_ID_PROPS,
                "recipientId": {"type": "string", "description": "Recipient id in the campaign."},
                "recipient_id": {"type": "string"},
                "title": {"type": "string"},
                "message": {"type": "string"},
            },
        ),
    },
    {
        "name": "monitor_campaign",
        "description": (
            "Watch a campaign as it happens: live funnel stats, the calls in flight RIGHT NOW, "
            "and recent calls — each with a portal link to open and listen/watch (live transcript "
            "while the call is in progress), plus the developer-portal link for the whole campaign."
        ),
        "inputSchema": _main_schema(dict(_CAMPAIGN_ID_PROPS)),
    },
    {
        "name": "get_call",
        "description": (
            "One call's record — while the call is in_progress the transcript grows on every "
            "poll, so repeated calls of this tool follow the live conversation."
        ),
        "inputSchema": _main_schema(
            {
                "callId": {"type": "string", "description": "Call record id."},
                "call_id": {"type": "string"},
            },
        ),
    },
    {
        "name": "upload_signing_document",
        "description": (
            "Upload the PDF a campaign sends for e-signature (retainer, agreement…) from a "
            "LOCAL file path. The server auto-detects signature/date/initials lines and returns "
            "their exact placements (PDF points, origin bottom-left, 612x792 page) — apply them "
            "with set_signature_fields, adjusting or adding fields as needed."
        ),
        "inputSchema": _main_schema(
            {
                **_CAMPAIGN_ID_PROPS,
                "filePath": {"type": "string", "description": "Local path to the PDF file."},
                "file_path": {"type": "string"},
            },
        ),
    },
    {
        "name": "detect_signature_fields",
        "description": "Re-run signature/date/initials auto-detection on the campaign's uploaded signing PDF.",
        "inputSchema": _main_schema(dict(_CAMPAIGN_ID_PROPS)),
    },
    {
        "name": "set_signature_fields",
        "description": (
            "Place the signing fields on the campaign's uploaded PDF: pass fields "
            "[{key, type: signature|date|initials|text, label, required, placement: {page (0-indexed), "
            "x, y, width, height}}] in PDF points (origin bottom-left; US-Letter is 612x792 — e.g. "
            "a signature line near the bottom is y≈100-140). Start from upload_signing_document's "
            "detected placements, or place by convention for scanned PDFs. Merges with the stored "
            "document config and enables signing."
        ),
        "inputSchema": _main_schema(
            {
                **_CAMPAIGN_ID_PROPS,
                "fields": {
                    "type": "array",
                    "items": {"type": "object", "additionalProperties": True},
                    "description": "Placed fields with coordinates.",
                },
            },
        ),
    },
    {
        "name": "scan_brand",
        "description": (
            "Scan a website for its branding: business name, brand colors, logo, favicon, Open Graph "
            "title/description/image, page images, and key same-domain pages. The same detection that "
            "styles agents during onboarding, as plain data — use it to build on-brand agents, widgets, "
            "and campaign docs."
        ),
        "inputSchema": _main_schema(
            {"url": {"type": "string", "description": "Website URL, e.g. https://acmedental.com."}},
            ["url"],
        ),
    },
    {
        "name": "generate_intake_form",
        "description": (
            "Generate a guided intake form (an IntakeConfig script of message/ask/choose nodes) from a "
            "plain-language description of what to collect. Pass agentId to ground it in that agent's "
            "business + industry, and apply:true to write it onto the agent (switches the agent to "
            "guided-workflow chat mode)."
        ),
        "inputSchema": _main_schema(
            {
                "description": {
                    "type": "string",
                    "description": "What the form should collect, in plain English.",
                },
                "agentId": {"type": "string", "description": "Agent to generate for (see list_voice_agents)."},
                "agent_id": {"type": "string"},
                "industry": {"type": "string", "description": "Optional industry key override."},
                "apply": {
                    "type": "boolean",
                    "description": "Write the generated form onto the agent (requires agentId).",
                },
            },
            ["description"],
        ),
    },
    # --- campaign-as-code: the whole campaign as one YAML/JSON document -------
    {
        "name": "apply_campaign_config",
        "description": (
            "Apply a campaign-as-code YAML/JSON document (validated FIRST — errors come back without "
            "side effects). Upserts by slug; supports branding: and intake_form: blocks that restyle "
            "the campaign's agent and generate its intake form on apply. Pass the document as config "
            "text or filePath to a local file. launch:true starts REAL calls/emails — use deliberately."
        ),
        "inputSchema": _main_schema(
            {
                "config": {"type": "string", "description": "Campaign-as-code YAML or JSON document text."},
                "filePath": {
                    "type": "string",
                    "description": "Local path to a YAML/JSON campaign config file (alternative to config).",
                },
                "file_path": {"type": "string"},
                "launch": {"type": "boolean", "description": "Override the doc's launch flag."},
                "accountId": {"type": "string"},
                "account_id": {"type": "string"},
            },
        ),
    },
    {
        "name": "export_campaign_config",
        "description": (
            "Export a campaign as its canonical campaign-as-code YAML document — including stored "
            "branding and intake_form blocks. Round-trips through apply_campaign_config (same slug, "
            "launch stays false)."
        ),
        "inputSchema": _main_schema(dict(_CAMPAIGN_ID_PROPS)),
    },
    {
        "name": "generate_campaign_config",
        "description": (
            "Draft a campaign-as-code YAML document from a plain-language description (+ optional CSV "
            "of leads to inline as recipients). NO side effects — review/edit the doc, then run "
            "apply_campaign_config."
        ),
        "inputSchema": _main_schema(
            {
                "prompt": {"type": "string", "description": "Plain-language description of the campaign."},
                "csv": {"type": "string", "description": "Optional pasted CSV of leads (first row = header)."},
                "agentId": {"type": "string", "description": "Voice agent to pre-fill into the doc."},
                "agent_id": {"type": "string"},
                "accountId": {"type": "string"},
                "account_id": {"type": "string"},
            },
            ["prompt"],
        ),
    },
]


class SupafoneMCPServer:
    def __init__(self, *, sleep: Callable[[float], None] = time.sleep) -> None:
        self._sleep = sleep
        # Cached main-app JWT per base URL (minted from SUPAFONE_EMAIL/PASSWORD);
        # cleared + re-minted transparently on a 401.
        self._main_tokens: dict[str, str] = {}

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
        if name == "get_tester_capabilities":
            return self._hosted_client(arguments).tester.capabilities()
        if name == "test_phone_agent":
            to_number = _pick(arguments, "toNumber", "to_number")
            if not to_number:
                raise ToolError("toNumber is required in E.164 format, for example +14155550100")
            if arguments.get("authorized") is not True:
                raise ToolError("authorized=true is required — only test agents you own or may call")
            return self._hosted_client(arguments).tester.call(
                to_number=str(to_number),
                scenario=str(arguments.get("scenario") or "price_probe"),
                agent_label=str(_pick(arguments, "agentLabel", "agent_label") or "mcp-tester"),
                ai_provider=str(_pick(arguments, "aiProvider", "ai_provider") or "unknown"),
                telephony_provider=str(
                    _pick(arguments, "telephonyProvider", "telephony_provider") or "unknown"
                ),
                authorized=True,
            )
        if name in {"get_phone_test", "wait_for_phone_test"}:
            session_id = _pick(arguments, "sessionId", "session_id")
            if not session_id:
                raise ToolError("sessionId is required")
            tester = self._hosted_client(arguments).tester
            if name == "get_phone_test":
                return tester.session(str(session_id))
            return tester.wait(
                str(session_id),
                poll_seconds=_safe_float(
                    _pick(arguments, "pollSeconds", "poll_seconds"),
                    default=1.4,
                    minimum=0.5,
                    maximum=10.0,
                ),
                timeout_seconds=_safe_float(
                    _pick(arguments, "timeoutSeconds", "timeout_seconds"),
                    default=120.0,
                    minimum=1.0,
                    maximum=240.0,
                ),
            )
        if name == "generate_qa_scenarios":
            prompt = _pick(arguments, "agentPrompt", "agent_prompt")
            if not prompt:
                raise ToolError("agentPrompt is required")
            return self._hosted_client(arguments).qa.generate(
                str(prompt),
                count=_safe_int(arguments.get("count"), default=5, minimum=1, maximum=12),
            )
        if name == "list_qa_runs":
            return self._hosted_client(arguments).qa.history(
                agent=str(arguments.get("agent") or "builder"),
                limit=_safe_int(arguments.get("limit"), default=40, minimum=1, maximum=200),
            )
        if name == "run_watcher_qa":
            client = self._hosted_client(arguments)
            email = str(arguments.get("email") or _env("SUPAFONE_EMAIL") or "")
            password = str(arguments.get("password") or _env("SUPAFONE_PASSWORD") or "")
            if not email or not password:
                raise ToolError("Set SUPAFONE_EMAIL and SUPAFONE_PASSWORD (or pass email/password) for session-scoped QA")
            client.labs_login(email=email, password=password)
            scenarios = arguments.get("scenarios")
            return client.qa.run(
                scenarios=[str(item) for item in scenarios] if isinstance(scenarios, list) else None,
                turns=_safe_int(arguments.get("turns"), default=2, minimum=1, maximum=8),
            )
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
        # --- main-app: campaigns + real calls --------------------------------
        if name == "list_voice_agents":
            return self._main_api("GET", "/api/v1/agents", None, arguments)
        if name == "place_call":
            agent_id = _pick(arguments, "agentId", "agent_id")
            to_number = _pick(arguments, "toNumber", "to_number")
            if not agent_id:
                raise ToolError("agentId is required (use list_voice_agents to find one)")
            if not to_number:
                raise ToolError("toNumber is required (E.164, e.g. +15551234567)")
            return self._main_api(
                "POST",
                "/api/v1/phone/test-call",
                {"agent_id": str(agent_id), "to_number": str(to_number)},
                arguments,
            )
        if name == "list_campaigns":
            account_id = _pick(arguments, "accountId", "account_id")
            suffix = f"?{parse.urlencode({'account_id': account_id})}" if account_id else ""
            return self._main_api("GET", f"/api/v1/campaigns{suffix}", None, arguments)
        if name == "create_campaign":
            payload = {
                "name": str(arguments.get("name") or "New campaign"),
                "goal": str(arguments.get("goal") or "book"),
            }
            agent_id = _pick(arguments, "agentId", "agent_id")
            if agent_id:
                payload["agent_id"] = str(agent_id)
            account_id = _pick(arguments, "accountId", "account_id")
            if account_id:
                payload["account_id"] = str(account_id)
            return self._main_api("POST", "/api/v1/campaigns", payload, arguments)
        if name == "get_campaign":
            return self._main_api(
                "GET", f"/api/v1/campaigns/{self._campaign_id(arguments)}", None, arguments
            )
        if name == "update_campaign":
            payload: dict[str, Any] = {}
            for arg_keys, api_key in (
                (("name",), "name"),
                (("goal",), "goal"),
                (("agentId", "agent_id"), "agent_id"),
                (("emailSubject", "email_subject"), "email_subject"),
                (("emailBody", "email_body"), "email_body"),
            ):
                value = _pick(arguments, *arg_keys)
                if value is not None:
                    payload[api_key] = value
            if isinstance(arguments.get("cadence"), list):
                payload["cadence"] = arguments["cadence"]
            if isinstance(arguments.get("settings"), Mapping):
                payload["settings"] = dict(arguments["settings"])
            if not payload:
                raise ToolError("Nothing to update — pass name, goal, agentId, emailSubject, emailBody, cadence, or settings")
            return self._main_api(
                "PUT", f"/api/v1/campaigns/{self._campaign_id(arguments)}", payload, arguments
            )
        if name == "add_campaign_recipients":
            recipients = arguments.get("recipients")
            if not isinstance(recipients, list) or not recipients:
                raise ToolError("recipients must be a non-empty array of {name, phone, email, ...} rows")
            return self._main_api(
                "POST",
                f"/api/v1/campaigns/{self._campaign_id(arguments)}/recipients",
                {"recipients": [dict(r) for r in recipients if isinstance(r, Mapping)]},
                arguments,
            )
        if name == "list_campaign_recipients":
            return self._main_api(
                "GET", f"/api/v1/campaigns/{self._campaign_id(arguments)}/recipients", None, arguments
            )
        if name == "launch_campaign":
            return self._main_api(
                "POST", f"/api/v1/campaigns/{self._campaign_id(arguments)}/launch", {}, arguments
            )
        if name == "pause_campaign":
            return self._main_api(
                "POST", f"/api/v1/campaigns/{self._campaign_id(arguments)}/pause", {}, arguments
            )
        if name == "list_campaign_presets":
            built_in = self._main_api("GET", "/api/v1/campaigns/outbound-presets", None, arguments)
            result: dict[str, Any] = {
                "built_in": built_in.get("presets", built_in) if isinstance(built_in, Mapping) else built_in,
            }
            try:
                custom = self._main_api("GET", "/api/v1/campaigns/custom-presets", None, arguments)
                result["custom"] = custom.get("presets", custom) if isinstance(custom, Mapping) else custom
            except ToolError as exc:
                result["custom"] = []
                result["custom_presets_error"] = str(exc)
            return result
        if name == "apply_campaign_preset":
            preset_id = _pick(arguments, "presetId", "preset_id")
            if not preset_id:
                raise ToolError("presetId is required (see list_campaign_presets)")
            return self._main_api(
                "POST",
                f"/api/v1/campaigns/{self._campaign_id(arguments)}/apply-preset",
                {"preset_id": str(preset_id)},
                arguments,
            )
        if name == "create_sign_link":
            recipient_id = _pick(arguments, "recipientId", "recipient_id")
            if not recipient_id:
                raise ToolError("recipientId is required (see list_campaign_recipients)")
            payload = {}
            for key in ("title", "message"):
                if arguments.get(key):
                    payload[key] = str(arguments[key])
            return self._main_api(
                "POST",
                f"/api/v1/campaigns/{self._campaign_id(arguments)}/recipients/{recipient_id}/sign-link",
                payload,
                arguments,
            )
        if name == "monitor_campaign":
            campaign_id = self._campaign_id(arguments)
            activity = self._main_api(
                "GET", f"/api/v1/campaigns/{campaign_id}/activity", None, arguments
            )
            app_url = _env("SUPAFONE_APP_URL") or "https://app.supafone.ai"
            app_url = app_url.rstrip("/")
            calls = activity.get("calls") if isinstance(activity, Mapping) else None
            in_flight: list[dict[str, Any]] = []
            recent: list[dict[str, Any]] = []
            for call in calls or []:
                if not isinstance(call, Mapping):
                    continue
                entry = dict(call)
                call_id = str(entry.get("id") or "")
                entry["listen_url"] = f"{app_url}/app/calls?call={parse.quote(call_id)}"
                if str(entry.get("status") or "") in ("initiated", "dialing", "in_progress"):
                    in_flight.append(entry)
                else:
                    recent.append(entry)
            return {
                "campaign_id": campaign_id,
                "stats": activity.get("stats") if isinstance(activity, Mapping) else None,
                "in_flight": in_flight,
                "recent_calls": recent[:10],
                "portal_url": f"{app_url}/app/developer?campaign={parse.quote(campaign_id)}",
                "how_to_listen": (
                    "Open portal_url (or a call's listen_url) in the browser — in-flight calls "
                    "show a live view with the transcript growing as the conversation happens. "
                    "Or poll the get_call tool with a callId to follow the transcript here."
                ),
            }
        if name == "get_call":
            call_id = _pick(arguments, "callId", "call_id")
            if not call_id:
                raise ToolError("callId is required (see monitor_campaign)")
            return self._main_api("GET", f"/api/v1/calls/{parse.quote(str(call_id))}", None, arguments)
        if name == "upload_signing_document":
            file_path = _pick(arguments, "filePath", "file_path")
            if not file_path:
                raise ToolError("filePath is required (local path to the PDF)")
            path = os.path.expanduser(str(file_path))
            if not os.path.isfile(path):
                raise ToolError(f"No file at {path}")
            with open(path, "rb") as handle:
                data = handle.read()
            if not data.lstrip()[:5].startswith(b"%PDF-"):
                raise ToolError("That file doesn't look like a PDF")
            return self._main_upload(
                f"/api/v1/campaigns/{self._campaign_id(arguments)}/signing/document",
                filename=os.path.basename(path) or "document.pdf",
                data=data,
                arguments=arguments,
            )
        if name == "detect_signature_fields":
            return self._main_api(
                "POST",
                f"/api/v1/campaigns/{self._campaign_id(arguments)}/signing/detect-fields",
                {},
                arguments,
            )
        if name == "set_signature_fields":
            fields = arguments.get("fields")
            if not isinstance(fields, list) or not fields:
                raise ToolError(
                    "fields must be a non-empty array of {key, type, label, required, placement:{page,x,y,width,height}}"
                )
            campaign_id = self._campaign_id(arguments)
            # Merge onto the stored config so pdfUrl/storedName survive.
            current = self._main_api("GET", f"/api/v1/campaigns/{campaign_id}", None, arguments)
            campaign = current.get("campaign") if isinstance(current, Mapping) else {}
            settings_bag = dict((campaign or {}).get("settings") or {})
            native = dict(settings_bag.get("native_signing") or {})
            if not (native.get("pdfUrl") or native.get("storedName")):
                raise ToolError("Upload the signing PDF first (upload_signing_document)")
            native["enabled"] = True
            native["fields"] = [dict(f) for f in fields if isinstance(f, Mapping)]
            return self._main_api(
                "PUT",
                f"/api/v1/campaigns/{campaign_id}",
                {"settings": {**settings_bag, "native_signing": native}},
                arguments,
            )
        if name == "scan_brand":
            url = str(arguments.get("url") or "").strip()
            if not url:
                raise ToolError("url is required (the website to scan)")
            return self._main_api("POST", "/api/v1/agents/brand-scan", {"url": url}, arguments)
        if name == "generate_intake_form":
            description = str(arguments.get("description") or "").strip()
            if not description:
                raise ToolError("description is required — what should the form collect?")
            agent_id = _pick(arguments, "agentId", "agent_id")
            apply = bool(arguments.get("apply"))
            if apply and not agent_id:
                raise ToolError("apply:true needs an agentId (use list_voice_agents to find one)")
            payload: dict[str, Any] = {"description": description}
            if arguments.get("industry"):
                payload["industry"] = str(arguments["industry"])
            if agent_id:
                payload["apply"] = apply
                return self._main_api(
                    "POST",
                    f"/api/v1/agents/{parse.quote(str(agent_id))}/generate-intake",
                    payload,
                    arguments,
                )
            return self._main_api("POST", "/api/v1/agents/generate-intake", payload, arguments)
        # --- campaign-as-code -------------------------------------------------
        if name == "apply_campaign_config":
            payload = {"config": self._config_text(arguments)}
            account_id = _pick(arguments, "accountId", "account_id")
            if account_id:
                payload["account_id"] = str(account_id)
            if isinstance(arguments.get("launch"), bool):
                payload["launch"] = arguments["launch"]
            # Dry-run first so a bad document surfaces its full error list
            # (path-by-path) instead of the apply endpoint's truncated 400.
            report = self._main_api("POST", "/api/v1/campaigns/config/validate", payload, arguments)
            if isinstance(report, Mapping) and not report.get("valid", False):
                raise ToolError(
                    _json_dumps(
                        {
                            "valid": False,
                            "errors": report.get("errors") or [],
                            "warnings": report.get("warnings") or [],
                            "hint": "Fix the document and re-run apply_campaign_config — nothing was applied.",
                        }
                    )
                )
            return self._main_api("POST", "/api/v1/campaigns/config/apply", payload, arguments)
        if name == "export_campaign_config":
            return self._main_api(
                "GET", f"/api/v1/campaigns/{self._campaign_id(arguments)}/config", None, arguments
            )
        if name == "generate_campaign_config":
            prompt = str(arguments.get("prompt") or "").strip()
            if not prompt:
                raise ToolError("prompt is required — describe the campaign to draft")
            payload = {"prompt": prompt}
            if arguments.get("csv"):
                payload["csv"] = str(arguments["csv"])
            agent_id = _pick(arguments, "agentId", "agent_id")
            if agent_id:
                payload["agent_id"] = str(agent_id)
            account_id = _pick(arguments, "accountId", "account_id")
            if account_id:
                payload["account_id"] = str(account_id)
            return self._main_api("POST", "/api/v1/campaigns/config/generate", payload, arguments)
        raise ToolError(f"Unknown tool: {name}")

    def _config_text(self, arguments: Mapping[str, Any]) -> str:
        """The campaign-as-code document text: inline `config`, or read from a
        local `filePath` (same local-file seam as upload_signing_document)."""
        config = arguments.get("config")
        if isinstance(config, str) and config.strip():
            return config
        if isinstance(config, Mapping):  # tolerate an object — YAML is a JSON superset
            return json.dumps(config, indent=2)
        file_path = _pick(arguments, "filePath", "file_path")
        if not file_path:
            raise ToolError("Pass config (YAML/JSON document text) or filePath (a local .yaml/.yml/.json file)")
        path = os.path.expanduser(str(file_path))
        if not os.path.isfile(path):
            raise ToolError(f"No file at {path}")
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        if not text.strip():
            raise ToolError(f"{path} is empty")
        return text

    def _main_upload(
        self, path: str, *, filename: str, data: bytes, arguments: Mapping[str, Any]
    ) -> Any:
        """Multipart file POST to the main API with the same auth/retry as _main_api."""
        base = self._main_base(arguments)
        explicit = _pick(arguments, "token", "accessToken", "access_token") or _env(
            "SUPAFONE_TOKEN", "SUPAFONE_ACCESS_TOKEN", "SUPAFONE_JWT"
        )
        token = str(explicit) if explicit else (self._main_tokens.get(base) or self._main_login(base, arguments))
        status, body = self._main_upload_http(base + path, filename, data, token)
        if status == 401 and not explicit:
            self._main_tokens.pop(base, None)
            status, body = self._main_upload_http(base + path, filename, data, self._main_login(base, arguments))
        if status >= 400:
            raise ToolError(_json_dumps({"status": status, "body": body}))
        return body

    def _main_upload_http(self, url: str, filename: str, data: bytes, token: str) -> tuple[int, Any]:
        boundary = f"----supafone{os.urandom(12).hex()}"
        safe_name = filename.replace('"', "").replace("\\", "")[:120] or "document.pdf"
        body = b"".join(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="file"; filename="{safe_name}"\r\n'.encode(),
                b"Content-Type: application/pdf\r\n\r\n",
                data,
                f"\r\n--{boundary}--\r\n".encode(),
            ]
        )
        headers = {
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = request.Request(url, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=120) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, (json.loads(raw) if raw else {})
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed: Any = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
            return exc.code, parsed
        except error.URLError as exc:
            raise ToolError(f"Network error calling {url}: {exc.reason}") from exc

    # --- main-app auth + HTTP (campaigns / calls) ----------------------------

    def _campaign_id(self, arguments: Mapping[str, Any]) -> str:
        campaign_id = _pick(arguments, "campaignId", "campaign_id")
        if not campaign_id:
            raise ToolError("campaignId is required (use list_campaigns to find one)")
        return str(campaign_id)

    def _main_base(self, arguments: Mapping[str, Any]) -> str:
        base = (
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
        return str(base).rstrip("/")

    def _main_login(self, base: str, arguments: Mapping[str, Any]) -> str:
        email = _pick(arguments, "email") or _env("SUPAFONE_EMAIL")
        password = _pick(arguments, "password") or _env("SUPAFONE_PASSWORD")
        if not (email and password):
            raise ToolError(
                "Not authenticated: set SUPAFONE_TOKEN (an app.supafone.ai JWT), or "
                "SUPAFONE_EMAIL + SUPAFONE_PASSWORD, or pass token/email/password."
            )
        status, body = self._main_http(
            "POST", f"{base}/api/v1/auth/login", {"email": str(email), "password": str(password)}, None
        )
        if status != 200 or not isinstance(body, Mapping):
            raise ToolError(_json_dumps({"login_failed": True, "status": status, "body": body}))
        token = body.get("access_token") or body.get("token")
        if not token:
            raise ToolError("Login succeeded but no token was returned")
        self._main_tokens[base] = str(token)
        return str(token)

    def _main_api(
        self,
        method: str,
        path: str,
        payload: Optional[dict[str, Any]],
        arguments: Mapping[str, Any],
    ) -> Any:
        base = self._main_base(arguments)
        explicit = _pick(arguments, "token", "accessToken", "access_token") or _env(
            "SUPAFONE_TOKEN", "SUPAFONE_ACCESS_TOKEN", "SUPAFONE_JWT"
        )
        token = str(explicit) if explicit else (self._main_tokens.get(base) or self._main_login(base, arguments))

        status, body = self._main_http(method, base + path, payload, token)
        # An expired minted token gets one transparent re-login; an explicit
        # token is the caller's to refresh.
        if status == 401 and not explicit:
            self._main_tokens.pop(base, None)
            token = self._main_login(base, arguments)
            status, body = self._main_http(method, base + path, payload, token)
        if status >= 400:
            raise ToolError(_json_dumps({"status": status, "body": body}))
        return body

    def _main_http(
        self,
        method: str,
        url: str,
        payload: Optional[dict[str, Any]],
        token: Optional[str],
    ) -> tuple[int, Any]:
        """(status, parsed_json_or_text) — never raises on HTTP status codes so
        the caller can implement the 401 re-login without string-parsing."""
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers: dict[str, str] = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if payload is not None:
            headers["Content-Type"] = "application/json"
        req = request.Request(url, data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, (json.loads(raw) if raw else {})
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed: Any = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
            return exc.code, parsed
        except error.URLError as exc:
            raise ToolError(f"Network error calling {url}: {exc.reason}") from exc

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
            or _sl_token_env()
        )
        if not api_key:
            raise ToolError("Set SUPAFONE_TOKEN/SUPAFONE_API_KEY or pass apiKey")

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
        labs_base_url = (
            _pick(arguments, "labsApiBaseUrl", "labs_api_base_url", "labsBaseUrl", "labs_base_url")
            or _env("SUPAFONE_LABS_API_BASE_URL", "SUPAFONE_LABS_BASE_URL")
            or DEFAULT_LABS_API_BASE
        )
        return Supafone(
            api_key=str(api_key),
            labs_api_key=str(api_key),
            supafone_api_base_url=str(base_url),
            labs_api_base_url=str(labs_base_url),
        )

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
            or _sl_token_env()
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
