"""``supafone`` — the general command-line client for the Supafone platform.

A thin wrapper over the public :class:`supafone_labs.client.Supafone` SDK and
the REST contracts it already speaks. Every command is one SDK call, or — where
a lifecycle genuinely needs more than one — an explicitly sequenced set of them
whose partial outcome is reported rather than hidden. The CLI never invents
behavior the SDK does not have.

Output is a stable JSON envelope by default (``--output json``)::

    {"ok": bool, "command": str, "data": any|null,
     "error": {"type", "message", "status", ...}|null, "warnings": [str]}

``--output text`` renders the same envelope for humans. Credentials are never
printed: secret-looking fields are masked and the resolved credential values are
scrubbed from every rendered byte.

Exit codes are stable:

* ``0`` — success
* ``1`` — the remote API returned an error, or it could not be reached
* ``2`` — usage / local / confirmation error (nothing was sent)
* ``3`` — partial failure: an earlier step of a multi-step command succeeded and
  the payload names exactly what landed and how to finish or undo it
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib import error as urlerror

from supafone_labs.client import (
    DEFAULT_LABS_API_BASE,
    DEFAULT_SUPAFONE_API_BASE,
    Supafone,
    SupafoneError,
)

EXIT_OK = 0
EXIT_API_ERROR = 1
EXIT_USAGE = 2
EXIT_PARTIAL = 3

PROG = "supafone"

# Field names whose *string* values are credentials. Matched on the whole key or
# on a `_`-delimited suffix, so `auth_token` and `twilio_auth_token` both mask
# while `token_count` does not.
_SECRET_SUFFIXES = (
    "api_key",
    "apikey",
    "access_token",
    "auth_token",
    "authorization",
    "bearer",
    "client_secret",
    "credential",
    "credentials",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "session_token",
    "signing_key",
    "token",
)

# Identifiers and derived values that merely *mention* a secret are safe to show.
_SECRET_EXEMPT_SUFFIXES = (
    "_count",
    "_fingerprint",
    "_hash",
    "_id",
    "_last4",
    "_masked",
    "_present",
    "_ref",
    "_sid",
    "_url",
)


class CliError(Exception):
    """A local (pre-flight) failure — nothing was sent to the API."""


class PartialFailure(Exception):
    """A multi-step command failed after an earlier step already landed."""

    def __init__(
        self,
        message: str,
        *,
        data: Any,
        failed_step: str,
        completed_steps: Sequence[str],
        remediation: str,
        status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.data = data
        self.failed_step = failed_step
        self.completed_steps = list(completed_steps)
        self.remediation = remediation
        self.status = status


# --------------------------------------------------------------------------
# redaction
# --------------------------------------------------------------------------


def _mask_secret(value: str) -> str:
    """A stable, non-reversible display form for a credential."""
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:3]}***{value[-4:]}"


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12] if value else ""


def _mask_email(value: str) -> str:
    if "@" not in value:
        return _mask_secret(value)
    local, _, domain = value.partition("@")
    head = local[:1] if local else ""
    return f"{head}***@{domain}"


def _is_secret_key(key: str) -> bool:
    normalized = str(key).strip().lower()
    if normalized.endswith(_SECRET_EXEMPT_SUFFIXES):
        return False
    return any(
        normalized == suffix or normalized.endswith(f"_{suffix}")
        for suffix in _SECRET_SUFFIXES
    )


def _scrub_text(text: str, secrets: Sequence[str]) -> str:
    for secret in secrets:
        if len(secret) >= 8 and secret in text:
            text = text.replace(secret, _mask_secret(secret))
    return text


def redact(value: Any, secrets: Sequence[str] = ()) -> Any:
    """Mask credential-shaped fields and scrub known secret values anywhere."""
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if _is_secret_key(key) and isinstance(item, str) and item:
                out[str(key)] = _mask_secret(item)
            else:
                out[str(key)] = redact(item, secrets)
        return out
    if isinstance(value, (list, tuple)):
        return [redact(item, secrets) for item in value]
    if isinstance(value, str):
        return _scrub_text(value, secrets)
    return value


# --------------------------------------------------------------------------
# envelope + rendering
# --------------------------------------------------------------------------


def envelope(
    command: str,
    *,
    data: Any = None,
    error: Mapping[str, Any] | None = None,
    warnings: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "ok": error is None,
        "command": command,
        "data": data,
        "error": dict(error) if error is not None else None,
        "warnings": list(warnings),
    }


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "-"
    if isinstance(value, (list, tuple)):
        return ", ".join(_scalar(item) for item in value)
    return str(value)


def _render_value(value: Any, indent: int) -> list[str]:
    pad = " " * indent
    lines: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(item, Mapping):
                lines.append(f"{pad}{key}:")
                lines.extend(_render_value(item, indent + 2))
            elif isinstance(item, (list, tuple)) and any(
                isinstance(row, (Mapping, list, tuple)) for row in item
            ):
                lines.append(f"{pad}{key}: ({len(item)})")
                lines.extend(_render_value(list(item), indent + 2))
            else:
                lines.append(f"{pad}{key}: {_scalar(item)}")
    elif isinstance(value, (list, tuple)):
        for position, item in enumerate(value):
            if isinstance(item, (Mapping, list, tuple)):
                lines.append(f"{pad}[{position}]")
                lines.extend(_render_value(item, indent + 2))
            else:
                lines.append(f"{pad}- {_scalar(item)}")
    else:
        lines.append(f"{pad}{_scalar(value)}")
    return lines


def render_text(result: Mapping[str, Any]) -> str:
    lines: list[str] = []
    if result.get("ok"):
        lines.append(f"ok  {result.get('command')}")
    else:
        error = dict(result.get("error") or {})
        status = error.get("status")
        suffix = f" {status}" if status is not None else ""
        lines.append(f"error  {result.get('command')}  [{error.get('type')}{suffix}]")
        lines.append(f"  {error.get('message')}")
        for key in ("failed_step", "completed_steps", "remediation"):
            if error.get(key):
                lines.append(f"  {key}: {_scalar(error[key])}")
    for warning in result.get("warnings") or []:
        lines.append(f"warning  {warning}")
    data = result.get("data")
    if data is not None:
        lines.extend(_render_value(data, 2))
    return "\n".join(lines)


def _simulation_warnings(data: Any) -> list[str]:
    """Surface the free-simulation vs. real-carrier distinction from responses.

    Supafone degrades to an in-memory simulation whenever Twilio is not
    configured, and every carrier-touching response carries ``simulated``. A
    caller must never confuse a free simulated purchase/dial with a billable
    real one, so it is promoted out of the payload into a warning.
    """
    found: list[bool] = []

    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            if isinstance(value.get("simulated"), bool):
                found.append(bool(value["simulated"]))
            for item in value.values():
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)

    walk(data)
    if not found:
        return []
    if all(found):
        return [
            (
                "simulated: no carrier action occurred and nothing was billed "
                "(Twilio is not configured for this account)"
            )
        ]
    if any(found):
        return ["mixed simulated and real carrier results — check `simulated` per record"]
    return ["real carrier action: this was billable"]


# --------------------------------------------------------------------------
# credentials + client
# --------------------------------------------------------------------------


def _read_key_file(path: str) -> str:
    try:
        text = Path(path).expanduser().read_text(encoding="utf-8")
    except OSError as exc:
        raise CliError(f"could not read --api-key-file: {exc}") from exc
    return text.strip()


def resolve_api_key(args: argparse.Namespace, *, stdin: Any = None) -> tuple[str, str]:
    """Return ``(key, source)``. The literal ``--api-key`` is supported but is
    the least safe source — it is visible in the process table and shell
    history, so ``--api-key-file`` / ``--api-key-stdin`` / the environment are
    preferred and the CLI says so once per invocation."""
    if getattr(args, "api_key", None):
        return str(args.api_key).strip(), "flag:--api-key"
    if getattr(args, "api_key_file", None):
        key = _read_key_file(str(args.api_key_file))
        if not key:
            raise CliError(f"--api-key-file {args.api_key_file} is empty")
        return key, "flag:--api-key-file"
    if getattr(args, "api_key_stdin", False):
        stream = stdin if stdin is not None else sys.stdin
        key = (stream.read() or "").strip()
        if not key:
            raise CliError("--api-key-stdin received no key on stdin")
        return key, "flag:--api-key-stdin"
    for name in ("SUPAFONE_API_KEY", "SUPAFONE_LABS_API_KEY"):
        value = os.getenv(name, "").strip()
        if value:
            return value, f"env:{name}"
    raise CliError(
        "no API key: set SUPAFONE_API_KEY, or pass --api-key-file / --api-key-stdin "
        "(--api-key takes a literal but is visible in the process table)"
    )


def collect_secrets(api_key: str) -> list[str]:
    """Every credential this process holds, for output scrubbing."""
    values = [api_key]
    for name in (
        "SUPAFONE_API_KEY",
        "SUPAFONE_LABS_API_KEY",
        "SUPAFONE_TOKEN",
        "SUPAFONE_ACCESS_TOKEN",
        "SUPAFONE_PASSWORD",
    ):
        value = os.getenv(name, "")
        if value:
            values.append(value)
    return [value for value in dict.fromkeys(values) if value]


def build_client(args: argparse.Namespace, api_key: str) -> Supafone:
    return Supafone(
        api_key=api_key,
        supafone_api_base_url=args.base_url,
        labs_api_base_url=args.labs_base_url,
        timeout=args.timeout,
    )


# --------------------------------------------------------------------------
# argument helpers
# --------------------------------------------------------------------------


def _parse_set(pairs: Sequence[str] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for pair in pairs or []:
        key, sep, raw = str(pair).partition("=")
        if not sep or not key.strip():
            raise CliError(f"--set expects key=value, got {pair!r}")
        try:
            out[key.strip()] = json.loads(raw)
        except json.JSONDecodeError:
            out[key.strip()] = raw
    return out


def _read_json_file(path: str, *, label: str) -> Any:
    try:
        text = Path(path).expanduser().read_text(encoding="utf-8")
    except OSError as exc:
        raise CliError(f"could not read {label}: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise CliError(f"{label} is not valid JSON: {exc}") from exc


def _read_text_file(path: str, *, label: str) -> str:
    try:
        return Path(path).expanduser().read_text(encoding="utf-8")
    except OSError as exc:
        raise CliError(f"could not read {label}: {exc}") from exc


def _config_payload(
    args: argparse.Namespace,
    *,
    label: str,
    fields: Sequence[tuple[str, str]] = (),
) -> dict[str, Any]:
    """Build a structured SDK payload without evaluating user input."""
    data: dict[str, Any] = {}
    if getattr(args, "config_file", None):
        loaded = _read_json_file(str(args.config_file), label="--config-file")
        if not isinstance(loaded, Mapping):
            raise CliError("--config-file must contain a JSON object")
        data.update(loaded)
    for attribute, key in fields:
        value = getattr(args, attribute, None)
        if value is not None:
            data[key] = value
    credentials_file = getattr(args, "credentials_file", None)
    if credentials_file:
        credentials = _read_json_file(str(credentials_file), label="--credentials-file")
        if not isinstance(credentials, Mapping):
            raise CliError("--credentials-file must contain a JSON object")
        data["credentials"] = dict(credentials)
    data.update(_parse_set(getattr(args, "set", None)))
    if not data:
        raise CliError(
            f"{label} requires --config-file, --set, or at least one explicit field"
        )
    if getattr(args, "agency_id", None):
        data.setdefault("agency_id", args.agency_id)
    return data


def _require_confirmation(actual: str | None, expected: str, *, action: str) -> None:
    if (actual or "") != expected:
        raise CliError(f'{action} requires the exact flag --confirm "{expected}"')


def agent_config(args: argparse.Namespace) -> dict[str, Any]:
    """Assemble the flat hosted-agent config the SDK expects."""
    data: dict[str, Any] = {}
    if getattr(args, "config_file", None):
        loaded = _read_json_file(str(args.config_file), label="--config-file")
        if not isinstance(loaded, Mapping):
            raise CliError("--config-file must contain a JSON object")
        data.update(loaded)
    simple = (
        ("name", "name"),
        ("assistant_name", "assistant_name"),
        ("business_name", "business_name"),
        ("industry", "industry"),
        ("website_url", "website_url"),
        ("goal", "goal"),
        ("greeting", "greeting"),
        ("system_prompt", "system_prompt"),
        ("language", "language"),
        ("preset_key", "preset_key"),
        ("agent_type", "agent_type"),
    )
    for attribute, key in simple:
        value = getattr(args, attribute, None)
        if value:
            data[key] = value
    voice = {
        key: getattr(args, attribute)
        for key, attribute in (
            ("provider", "voice_provider"),
            ("voice_id", "voice_id"),
            ("model", "voice_model"),
        )
        if getattr(args, attribute, None)
    }
    if voice:
        data["voice"] = {**dict(data.get("voice") or {}), **voice}
    supervisor = getattr(args, "supervisor", None)
    if supervisor == "off":
        data["supervisor"] = False
    elif supervisor == "managed":
        data["supervisor"] = {"enabled": True, "mode": "managed"}
    elif supervisor:
        default_env = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "groq": "GROQ_API_KEY",
            "cerebras": "CEREBRAS_API_KEY",
        }[supervisor]
        env_name = getattr(args, "supervisor_api_key_env", None) or default_env
        api_key = os.getenv(env_name, "")
        if not api_key:
            raise CliError(
                f"BYOK Supervisor requires {env_name}; set it or pass "
                "--supervisor-api-key-env with the name of an existing environment variable"
            )
        data["supervisor"] = {
            "enabled": True,
            "mode": "byok",
            "provider": supervisor,
            "model": getattr(args, "supervisor_model", None),
            "api_key": api_key,
        }
    data.update(_parse_set(getattr(args, "set", None)))
    if getattr(args, "agency_id", None):
        data.setdefault("agency_id", args.agency_id)
    if not data.get("name"):
        raise CliError("agents create requires --name (or a name in --config-file/--set)")
    return data


def extract_agent_key(created: Any, config: Mapping[str, Any]) -> str:
    """Mirror the SDK's own agent-key resolution for created agents."""
    if isinstance(created, Mapping):
        inner = created.get("agent")
        if isinstance(inner, Mapping):
            for key in ("agent_key", "agentKey", "id"):
                if inner.get(key):
                    return str(inner[key])
        for key in ("agent_key", "agentKey"):
            if created.get(key):
                return str(created[key])
    for key in ("agent_key", "agentKey"):
        if config.get(key):
            return str(config[key])
    return ""


# --------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Supafone platform CLI — hosted agents, managed numbers, QA, voices, "
            "and campaigns over the public Supafone SDK."
        ),
    )
    credential = parser.add_mutually_exclusive_group()
    credential.add_argument(
        "--api-key",
        help=(
            "Literal API key. Visible in the process table and shell history — "
            "prefer SUPAFONE_API_KEY, --api-key-file, or --api-key-stdin."
        ),
    )
    credential.add_argument("--api-key-file", help="Read the API key from a file.")
    credential.add_argument(
        "--api-key-stdin",
        action="store_true",
        help="Read the API key from stdin.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("SUPAFONE_API_BASE_URL", DEFAULT_SUPAFONE_API_BASE),
        help="Supafone product API origin (or SUPAFONE_API_BASE_URL).",
    )
    parser.add_argument(
        "--labs-base-url",
        default=os.getenv("SUPAFONE_LABS_API_BASE_URL", DEFAULT_LABS_API_BASE),
        help="Supafone Labs cloud API origin (or SUPAFONE_LABS_API_BASE_URL).",
    )
    parser.add_argument(
        "--agency-id",
        default=os.getenv("SUPAFONE_AGENCY_ID", "") or None,
        help="Act on this agency/account UUID (or SUPAFONE_AGENCY_ID).",
    )
    default_output = os.getenv("SUPAFONE_OUTPUT", "json")
    parser.add_argument(
        "--output",
        choices=("json", "text"),
        default=default_output if default_output in ("json", "text") else "json",
        help="json (stable envelope, default) or text (human-readable).",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds.")

    groups = parser.add_subparsers(dest="group", required=True)
    _account_commands(groups)
    _capabilities_command(groups)
    _agent_commands(groups)
    _tool_commands(groups)
    _runtime_commands(groups)
    _telephony_commands(groups)
    _call_commands(groups)
    _recording_commands(groups)
    _transcript_commands(groups)
    _knowledge_commands(groups)
    _activity_commands(groups)
    _plan_commands(groups)
    _number_commands(groups)
    _qa_commands(groups)
    _voice_commands(groups)
    _campaign_commands(groups)
    return parser


def _account_commands(groups: Any) -> None:
    account = groups.add_parser("account", help="Credential, usage, and balance surface.")
    commands = account.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "show",
        help="Redacted summary of the resolved credentials and endpoints (no network).",
    )
    commands.add_parser("usage", help="Today's managed Supervisor/TTS/STT usage.")
    commands.add_parser("balance", help="Remaining prepaid Supafone Labs minute balance.")
    checkout = commands.add_parser(
        "checkout", help="Create a Stripe Checkout link for managed minutes."
    )
    checkout.add_argument("--sku", default="sf_voice_minutes_400_v1")


def _capabilities_command(groups: Any) -> None:
    capabilities = groups.add_parser(
        "capabilities",
        help="The hosted provisioning contract: fields, runtimes, telephony, presets, voices.",
    )
    capabilities.set_defaults(command="show")


def _agent_commands(groups: Any) -> None:
    agents = groups.add_parser("agents", help="Hosted Supafone voice agents.")
    commands = agents.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="Create a hosted agent.")
    create.add_argument("--name", help="Human-readable agent name (required).")
    create.add_argument(
        "--direction",
        choices=("inbound", "outbound"),
        default="inbound",
        help="Agent direction; selects the matching preset defaults.",
    )
    create.add_argument("--assistant-name")
    create.add_argument("--business-name")
    create.add_argument("--industry")
    create.add_argument("--website-url")
    create.add_argument("--goal")
    create.add_argument("--greeting")
    create.add_argument("--system-prompt")
    create.add_argument("--language")
    create.add_argument("--preset-key")
    create.add_argument("--agent-type")
    create.add_argument("--voice-provider")
    create.add_argument("--voice-id")
    create.add_argument("--voice-model")
    create.add_argument(
        "--supervisor",
        choices=(
            "managed",
            "off",
            "anthropic",
            "openai",
            "gemini",
            "openrouter",
            "groq",
            "cerebras",
        ),
        help="Use managed supervision, disable it, or choose a BYOK reasoning provider.",
    )
    create.add_argument(
        "--supervisor-model",
        help="Override the provider's default Supervisor model.",
    )
    create.add_argument(
        "--supervisor-api-key-env",
        help=(
            "Environment variable containing the BYOK Supervisor key; "
            "the key is never accepted as a CLI flag."
        ),
    )
    create.add_argument("--config-file", help="JSON file with the flat agent config.")
    create.add_argument(
        "--set",
        action="append",
        metavar="KEY=VALUE",
        help="Set any additional flat config key (JSON value when parseable). Repeatable.",
    )
    create.add_argument(
        "--with-number",
        action="store_true",
        help="Also buy and assign a managed number (BILLABLE; needs --confirm-purchase).",
    )
    create.add_argument("--area-code", help="Area code for --with-number.")
    create.add_argument("--phone-number", help="Exact number to buy for --with-number.")
    create.add_argument(
        "--confirm-purchase",
        action="store_true",
        help="Acknowledge that --with-number buys a number and is billable.",
    )

    listing = commands.add_parser("list", help="List hosted agents.")
    listing.add_argument("--agent-type", help="Filter by agent type (phone, campaign, web...).")

    get = commands.add_parser("get", help="Read one hosted agent.")
    get.add_argument("agent_key")

    update = commands.add_parser("update", help="Update a hosted agent in place.")
    update.add_argument("agent_key")
    update.add_argument("--name")
    update.add_argument("--assistant-name")
    update.add_argument("--business-name")
    update.add_argument("--website-url")
    update.add_argument("--goal")
    update.add_argument("--greeting")
    update.add_argument("--system-prompt")
    update.add_argument("--language")
    update.add_argument("--config-file", help="JSON object with agent fields to update.")
    update.add_argument(
        "--set",
        action="append",
        metavar="KEY=VALUE",
        help="Set an additional update field (JSON value when parseable). Repeatable.",
    )

    readiness = commands.add_parser("readiness", help="Check whether an agent can go live.")
    readiness.add_argument("agent_key")
    activate = commands.add_parser("activate", help="Activate a ready hosted agent.")
    activate.add_argument("agent_key")
    pause = commands.add_parser("pause", help="Pause a hosted agent without deleting it.")
    pause.add_argument("agent_key")

    delete = commands.add_parser("delete", help="Delete a hosted agent (irreversible).")
    delete.add_argument("agent_key")
    delete.add_argument(
        "--confirm",
        help='Exact acknowledgement: "DELETE AGENT <agent_key>".',
    )
    delete.add_argument(
        "--release-numbers",
        action="store_true",
        help="Also release the agent's managed numbers back to the carrier.",
    )


def _tool_commands(groups: Any) -> None:
    tools = groups.add_parser("tools", help="Built-in hosted runtime tools.")
    commands = tools.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="List tools available to hosted agents.")


def _runtime_commands(groups: Any) -> None:
    runtime = groups.add_parser("runtime", help="Hosted realtime runtime configuration.")
    commands = runtime.add_subparsers(dest="command", required=True)
    commands.add_parser("get", help="Read masked runtime configuration.")
    update = commands.add_parser("update", help="Configure the hosted realtime runtime.")
    update.add_argument("--provider")
    update.add_argument("--credentials-file", help="JSON credentials object; never echoed.")
    update.add_argument("--config-file", help="Complete runtime JSON object.")
    update.add_argument("--set", action="append", metavar="KEY=VALUE")


def _telephony_commands(groups: Any) -> None:
    telephony = groups.add_parser("telephony", help="Managed or BYOK carrier configuration.")
    commands = telephony.add_subparsers(dest="command", required=True)
    commands.add_parser("get", help="Read masked telephony configuration.")
    update = commands.add_parser("update", help="Configure managed or BYOK telephony.")
    update.add_argument("--mode", choices=("supafone_managed", "byok"))
    update.add_argument("--provider")
    update.add_argument("--credentials-file", help="JSON credentials object; never echoed.")
    update.add_argument("--config-file", help="Complete telephony JSON object.")
    update.add_argument("--set", action="append", metavar="KEY=VALUE")


def _call_commands(groups: Any) -> None:
    calls = groups.add_parser("calls", help="Durable hosted call records.")
    commands = calls.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="List calls for this account.")
    listing.add_argument("--agent-key")
    listing.add_argument("--limit", type=int, default=50)
    listing.add_argument("--offset", type=int, default=0)
    get = commands.add_parser("get", help="Read one call and its linked artifacts.")
    get.add_argument("call_id")
    delete = commands.add_parser("delete", help="Delete one call record (irreversible).")
    delete.add_argument("call_id")
    delete.add_argument("--confirm", help='Exact acknowledgement: "DELETE CALL <call_id>".')


def _recording_commands(groups: Any) -> None:
    recordings = groups.add_parser("recordings", help="Call recording artifacts.")
    commands = recordings.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="List recording artifacts.")
    listing.add_argument("--agent-key")
    listing.add_argument("--call-id")
    listing.add_argument("--limit", type=int, default=50)
    get = commands.add_parser("get", help="Read one signed recording artifact.")
    get.add_argument("recording_id")
    delete = commands.add_parser("delete", help="Delete a recording artifact (irreversible).")
    delete.add_argument("recording_id")
    delete.add_argument("--reason")
    delete.add_argument(
        "--confirm", help='Exact acknowledgement: "DELETE RECORDING <recording_id>".'
    )


def _transcript_commands(groups: Any) -> None:
    transcripts = groups.add_parser("transcripts", help="Call transcripts and summaries.")
    commands = transcripts.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="List transcript artifacts.")
    listing.add_argument("--agent-key")
    listing.add_argument("--call-id")
    listing.add_argument("--limit", type=int, default=50)
    get = commands.add_parser("get", help="Read one transcript artifact.")
    get.add_argument("transcript_id")


def _knowledge_commands(groups: Any) -> None:
    knowledge = groups.add_parser("knowledge", help="Agent website and document knowledge.")
    commands = knowledge.add_subparsers(dest="command", required=True)
    status = commands.add_parser("status", help="Read the agent's current knowledge status.")
    status.add_argument("agent_id")
    sync = commands.add_parser("website-sync", help="Scrape and rebuild website knowledge.")
    sync.add_argument("agent_id")
    sync.add_argument("--url", required=True)
    detach = commands.add_parser(
        "website-detach", help="Detach website knowledge while keeping documents."
    )
    detach.add_argument("agent_id")
    detach.add_argument(
        "--confirm", help='Exact acknowledgement: "DETACH WEBSITE <agent_id>".'
    )
    reindex = commands.add_parser("reindex", help="Rebuild the saved private corpus.")
    reindex.add_argument("agent_id")
    upload = commands.add_parser("document-upload", help="Upload and index one document.")
    upload.add_argument("agent_id")
    upload.add_argument("file")
    delete = commands.add_parser("document-delete", help="Delete one knowledge document.")
    delete.add_argument("agent_id")
    delete.add_argument("document_id")
    delete.add_argument(
        "--confirm", help='Exact acknowledgement: "DELETE DOCUMENT <document_id>".'
    )
    query = commands.add_parser("query", help="Ask a grounded question against the corpus.")
    query.add_argument("agent_id")
    source = query.add_mutually_exclusive_group(required=True)
    source.add_argument("--message")
    source.add_argument("--message-file")
    query.add_argument("--history-file", help="Optional JSON array of prior chat messages.")


def _activity_commands(groups: Any) -> None:
    activity = groups.add_parser("activity", help="Durable account activity events.")
    commands = activity.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="List filtered activity events.")
    listing.add_argument("--event-type")
    listing.add_argument("--resource-type")
    listing.add_argument("--resource-id")
    listing.add_argument("--limit", type=int, default=50)
    listing.add_argument("--offset", type=int, default=0)


def _plan_commands(groups: Any) -> None:
    plans = groups.add_parser("plans", help="Persisted generated agent plans.")
    commands = plans.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="List generated plans.")
    listing.add_argument("--resource-id")
    listing.add_argument("--limit", type=int, default=50)
    listing.add_argument("--offset", type=int, default=0)


def _number_commands(groups: Any) -> None:
    numbers = groups.add_parser("numbers", help="Supafone-managed phone numbers.")
    commands = numbers.add_subparsers(dest="command", required=True)

    search = commands.add_parser("search", help="Search purchasable managed numbers.")
    search.add_argument("--area-code")
    search.add_argument("--country-code", default="US")
    search.add_argument("--contains")
    search.add_argument("--number-type")
    search.add_argument("--limit", type=int, default=6)

    listing = commands.add_parser("list", help="List the account's managed numbers.")
    listing.add_argument("--active-only", action="store_true")

    commands.add_parser(
        "pool",
        help="Show explicitly enrolled shared developer numbers and their live status.",
    )
    watch = commands.add_parser(
        "watch",
        help="Stream shared developer-number availability over a scoped WebSocket.",
    )
    watch.add_argument(
        "--events",
        type=int,
        default=0,
        help="Stop after N events; 0 keeps watching until interrupted.",
    )

    buy = commands.add_parser(
        "buy",
        help="Buy a managed number and attach it to an agent (BILLABLE).",
    )
    buy.add_argument(
        "--agent-key",
        required=True,
        help="The number is provisioned onto this agent; the API requires it.",
    )
    buy.add_argument("--phone-number", help="Exact number to buy (else one is searched).")
    buy.add_argument("--area-code", help="Area code to search when --phone-number is omitted.")
    buy.add_argument("--friendly-name")
    buy.add_argument(
        "--confirm-purchase",
        action="store_true",
        help="Required. Acknowledges a billable carrier purchase.",
    )

    assign = commands.add_parser("assign", help="Assign an owned number to an agent.")
    assign.add_argument("number_id", help="Number id or E.164 number.")
    assign.add_argument("--agent-key", required=True)
    assign.add_argument("--friendly-name")

    unassign = commands.add_parser(
        "unassign",
        help="Detach a number from its agent; the account keeps the number.",
    )
    unassign.add_argument("number_id")
    unassign.add_argument("--reason")

    release = commands.add_parser(
        "release",
        help="Release a number back to the carrier (irreversible).",
    )
    release.add_argument("number_id")
    release.add_argument(
        "--confirm",
        help='Exact acknowledgement: "RELEASE NUMBER <number_id>".',
    )
    release.add_argument("--reason")
    release.add_argument(
        "--keep-out-of-pool",
        action="store_true",
        help="Do not return the number to the Supafone pool.",
    )


def _qa_commands(groups: Any) -> None:
    qa = groups.add_parser("qa", help="Adversarial QA and authorized PSTN tests.")
    commands = qa.add_subparsers(dest="command", required=True)

    generate = commands.add_parser(
        "generate",
        help="Generate adversarial scenarios from an agent prompt (free, no calls).",
    )
    source = generate.add_mutually_exclusive_group(required=True)
    source.add_argument("--agent-prompt")
    source.add_argument("--agent-prompt-file")
    generate.add_argument("--count", type=int, default=5)

    twin = commands.add_parser(
        "twin",
        help=(
            "Run the QA Twin suite: scenarios generated from the agent's own "
            "objective, played as simulated calls against the configured agent. "
            "Free simulation — no carrier audio."
        ),
    )
    twin.add_argument("--count", type=int, default=4)
    twin.add_argument("--turns", type=int, default=2)
    twin.add_argument(
        "--supervised",
        action="store_true",
        help="Play the suite with the Labs watcher whispering.",
    )

    battle = commands.add_parser(
        "battle",
        help=(
            "Run the A/B QA battle: every scenario plays once unsupervised and "
            "once watched; the delta is the supervision lift. Free simulation."
        ),
    )
    battle.add_argument(
        "--scenario",
        action="append",
        help="Scenario id to play. Repeatable; omit for the key's default set.",
    )
    battle.add_argument("--turns", type=int, default=2)

    history = commands.add_parser("history", help="Past QA runs for an agent.")
    history.add_argument("--agent", default="builder")
    history.add_argument("--limit", type=int, default=40)

    pstn = commands.add_parser(
        "pstn-test",
        help=(
            "Place ONE authorized real-audio PSTN test call to a number you "
            "control. BILLABLE and rate-limited; this is not the free simulation."
        ),
    )
    pstn.add_argument("--agent-id", required=True, help="Account voice agent id.")
    pstn.add_argument("--to", dest="to_number", required=True, help="E.164 destination you own.")
    pstn.add_argument(
        "--confirm",
        help='Exact acknowledgement: "AUTHORIZED PSTN TEST <to-number>".',
    )

    status = commands.add_parser(
        "pstn-status",
        help="Read the status, transcript, and watcher events of a test call.",
    )
    status.add_argument("call_id", help="The call_record_id returned by qa pstn-test.")


def _voice_commands(groups: Any) -> None:
    voices = groups.add_parser("voices", help="Provider-authorized voice catalog.")
    commands = voices.add_subparsers(dest="command", required=True)

    listing = commands.add_parser("list", help="Search the voice catalog.")
    listing.add_argument("--provider")
    listing.add_argument("--search")
    listing.add_argument("--language")
    listing.add_argument("--cursor", type=int)
    listing.add_argument("--limit", type=int, default=50)

    preview = commands.add_parser(
        "preview",
        help=(
            "Preview METADATA for one voice — provider, language, and the "
            "preview URL. No audio is downloaded and nothing is billed."
        ),
    )
    preview.add_argument("voice_id")
    preview.add_argument("--provider")


def _campaign_commands(groups: Any) -> None:
    campaign = groups.add_parser("campaign", help="Campaign-as-code validate/generate/run.")
    commands = campaign.add_subparsers(dest="command", required=True)

    validate = commands.add_parser(
        "validate",
        help="Validate a campaign document with no side effects.",
    )
    validate.add_argument("file", help="Campaign-as-code YAML or JSON document.")
    validate.add_argument(
        "--assume-launch",
        action="store_true",
        help="Also apply launch-time validation rules (still no side effects).",
    )

    generate = commands.add_parser(
        "generate",
        help="Draft a campaign document from a plain-language description.",
    )
    generate.add_argument("prompt")
    generate.add_argument("--csv-file", help="CSV of leads to inform the draft.")
    generate.add_argument("--agent-id")

    apply = commands.add_parser(
        "apply",
        help="Upsert the campaign from a document without launching calls.",
    )
    apply.add_argument("file")

    run = commands.add_parser(
        "run",
        help=(
            "Validate, then hand the campaign off to the campaign engine with "
            "launch=true. Starts REAL outbound calls."
        ),
    )
    run.add_argument("file")
    run.add_argument("--confirm", help='Exact acknowledgement: "LAUNCH".')

    status = commands.add_parser("status", help="Campaign progress counters.")
    status.add_argument("campaign_id")


# --------------------------------------------------------------------------
# command implementations
# --------------------------------------------------------------------------


def _account_show(args: argparse.Namespace, api_key: str, source: str) -> dict[str, Any]:
    token = os.getenv("SUPAFONE_TOKEN", "") or os.getenv("SUPAFONE_ACCESS_TOKEN", "")
    email = os.getenv("SUPAFONE_EMAIL", "")
    password = os.getenv("SUPAFONE_PASSWORD", "")
    return {
        "api_base_url": args.base_url,
        "labs_api_base_url": args.labs_base_url,
        "agency_id": args.agency_id,
        "credentials": {
            "api_key": {
                "present": True,
                "source": source,
                "masked": _mask_secret(api_key),
                "fingerprint": _fingerprint(api_key),
                "doubles_as_account_token": api_key.startswith("sl_"),
            },
            "account_token": {
                "present": bool(token),
                "source": "env:SUPAFONE_TOKEN" if token else None,
                "masked": _mask_secret(token) if token else None,
            },
            "account_login": {
                "present": bool(email and password),
                "source": "env:SUPAFONE_EMAIL+SUPAFONE_PASSWORD" if email and password else None,
                "email": _mask_email(email) if email else None,
            },
        },
    }


def _agents_create(client: Supafone, args: argparse.Namespace) -> tuple[Any, list[str]]:
    config = agent_config(args)
    warnings: list[str] = []
    if args.with_number and not args.confirm_purchase:
        raise CliError(
            "--with-number buys a managed number from the carrier — pass "
            "--confirm-purchase to acknowledge the charge"
        )
    factory = (
        client.labs.agents.create_outbound
        if args.direction == "outbound"
        else client.labs.agents.create_inbound
    )
    created = factory(config)
    if not args.with_number:
        return created, warnings

    agent_key = extract_agent_key(created, config)
    if not agent_key:
        raise PartialFailure(
            "the agent was created but the response carried no agent key, so the "
            "number could not be provisioned",
            data={"agent": created},
            failed_step="phone_number",
            completed_steps=["agent"],
            remediation=(
                "find the agent with `supafone agents list`, then run "
                "`supafone numbers buy --agent-key <key> --confirm-purchase`"
            ),
        )
    number_request: dict[str, Any] = {"agent_key": agent_key, "agent_name": config.get("name")}
    if args.phone_number:
        number_request["phone_number"] = args.phone_number
    if args.area_code:
        number_request["area_code"] = args.area_code
        number_request["search"] = {"area_code": args.area_code, "limit": 1}
    if args.agency_id:
        number_request["agency_id"] = args.agency_id
    try:
        number = client.labs.phone_numbers.buy_and_assign(number_request)
    except SupafoneError as exc:
        raise PartialFailure(
            f"the agent was created but buying its number failed: {exc}",
            data={"agent": created, "agent_key": agent_key},
            failed_step="phone_number",
            completed_steps=["agent"],
            remediation=(
                f"retry with `supafone numbers buy --agent-key {agent_key} "
                f"--confirm-purchase`, or remove the agent with "
                f'`supafone agents delete {agent_key} --confirm "DELETE AGENT {agent_key}"`'
            ),
            status=exc.status,
        ) from exc
    return {**dict(created), "number": number}, warnings


def _numbers_buy(client: Supafone, args: argparse.Namespace) -> Any:
    if not args.confirm_purchase:
        raise CliError(
            "numbers buy charges the account for a carrier number — pass "
            "--confirm-purchase to proceed"
        )
    request: dict[str, Any] = {"agent_key": args.agent_key}
    if args.phone_number:
        request["phone_number"] = args.phone_number
    if args.area_code:
        request["area_code"] = args.area_code
        request["search"] = {"area_code": args.area_code, "limit": 1}
    if args.friendly_name:
        request["friendly_name"] = args.friendly_name
    if args.agency_id:
        request["agency_id"] = args.agency_id
    return client.labs.phone_numbers.buy_and_assign(request)


async def _numbers_watch(client: Supafone, args: argparse.Namespace) -> dict[str, Any]:
    seen = 0
    async for event in client.labs.phone_numbers.stream_pool():
        seen += 1
        _emit(
            envelope("numbers.watch", data=redact(event)),
            args.output,
            sys.stdout,
        )
        if args.events > 0 and seen >= args.events:
            break
    return {"events": seen, "stopped": "limit" if args.events > 0 else "stream_closed"}


def _voices_preview(client: Supafone, args: argparse.Namespace) -> tuple[Any, list[str]]:
    catalog = client.labs.voices.list(
        search=args.voice_id,
        provider=args.provider,
        limit=250,
        agency_id=args.agency_id,
    )
    rows = catalog.get("voices") if isinstance(catalog, Mapping) else None
    matches = [
        row
        for row in rows or []
        if isinstance(row, Mapping)
        and args.voice_id
        in {
            str(row.get("id") or ""),
            str(row.get("voice_id") or ""),
            str(row.get("provider_voice_id") or ""),
        }
    ]
    if not matches:
        raise CliError(
            f"voice {args.voice_id!r} is not in this account's catalog — "
            "search it with `supafone voices list --search ...`"
        )
    voice = dict(matches[0])
    warnings: list[str] = []
    if not voice.get("preview_url"):
        warnings.append("this voice has no preview audio URL in the catalog")
    return {
        "voice": voice,
        "preview": {
            "preview_url": voice.get("preview_url"),
            "endpoint": f"GET {args.base_url}/api/v1/labs/voices/preview?voice={voice.get('id')}",
            "audio_downloaded": False,
        },
    }, warnings


def _campaign_run(client: Supafone, args: argparse.Namespace) -> tuple[Any, list[str]]:
    _require_confirmation(args.confirm, "LAUNCH", action="campaign run")
    document = _read_text_file(args.file, label="campaign document")
    validation = client.campaigns.validate_config(document, launch=True)
    if isinstance(validation, Mapping) and validation.get("valid") is False:
        raise CliError(
            "campaign document did not validate for launch: "
            + json.dumps(validation.get("errors") or validation, default=str)
        )
    try:
        applied = client.campaigns.apply_config(document, launch=True)
    except SupafoneError as exc:
        raise PartialFailure(
            f"the document validated but the launch handoff failed: {exc}",
            data={"validation": validation},
            failed_step="launch",
            completed_steps=["validate"],
            remediation=(
                "no calls were started; re-run `supafone campaign run` once the "
                "error is resolved, or `supafone campaign apply` to upsert without launching"
            ),
            status=exc.status,
        ) from exc
    return (
        {
            "validation": validation,
            "applied": applied,
            "handoff": {
                "engine": "campaigns",
                "launched": True,
                "next": [
                    f"{PROG} campaign status <campaign_id>",
                    "supafone-campaign runs --limit 25",
                ],
            },
        },
        ["real outbound calls were handed off to the campaign engine"],
    )


def dispatch(client: Supafone, args: argparse.Namespace) -> tuple[Any, list[str]]:
    """Run one command. Returns ``(data, warnings)``."""
    group, command = args.group, args.command
    agency = args.agency_id

    if group == "capabilities":
        return client.labs.capabilities(), []

    if group == "account":
        if command == "usage":
            return client.usage(), []
        if command == "balance":
            return client.balance(), []
        if command == "checkout":
            return client.labs.billing.top_up(args.sku), []

    if group == "agents":
        if command == "create":
            return _agents_create(client, args)
        if command == "list":
            return client.labs.agents.list(agency_id=agency, agent_type=args.agent_type), []
        if command == "get":
            return client.labs.agents.get(args.agent_key, agency_id=agency), []
        if command == "update":
            config = _config_payload(
                args,
                label="agents update",
                fields=(
                    ("name", "name"),
                    ("assistant_name", "assistant_name"),
                    ("business_name", "business_name"),
                    ("website_url", "website_url"),
                    ("goal", "goal"),
                    ("greeting", "greeting"),
                    ("system_prompt", "system_prompt"),
                    ("language", "language"),
                ),
            )
            config.pop("agency_id", None)
            return client.labs.agents.update(args.agent_key, config, agency_id=agency), []
        if command == "readiness":
            return client.labs.agents.readiness(args.agent_key, agency_id=agency), []
        if command == "activate":
            return client.labs.agents.activate(args.agent_key, agency_id=agency), []
        if command == "pause":
            return client.labs.agents.pause(args.agent_key, agency_id=agency), []
        if command == "delete":
            _require_confirmation(
                args.confirm,
                f"DELETE AGENT {args.agent_key}",
                action="agents delete",
            )
            return (
                client.labs.agents.delete(
                    args.agent_key,
                    agency_id=agency,
                    release_numbers=args.release_numbers,
                ),
                (
                    ["the agent's managed numbers were released to the carrier"]
                    if args.release_numbers
                    else []
                ),
            )

    if group == "tools" and command == "list":
        return client.labs.tools.list(), []

    if group == "runtime":
        if command == "get":
            return client.labs.runtime.get(agency_id=agency), []
        if command == "update":
            config = _config_payload(
                args,
                label="runtime update",
                fields=(("provider", "provider"),),
            )
            return client.labs.runtime.configure(config), []

    if group == "telephony":
        if command == "get":
            return client.labs.telephony.get(agency_id=agency), []
        if command == "update":
            config = _config_payload(
                args,
                label="telephony update",
                fields=(("mode", "mode"), ("provider", "provider")),
            )
            return client.labs.telephony.configure(config), []

    if group == "calls":
        if command == "list":
            return (
                client.labs.calls.list(
                    agency_id=agency,
                    agent_key=args.agent_key,
                    limit=args.limit,
                    offset=args.offset,
                ),
                [],
            )
        if command == "get":
            return client.labs.calls.get(args.call_id, agency_id=agency), []
        if command == "delete":
            _require_confirmation(
                args.confirm,
                f"DELETE CALL {args.call_id}",
                action="calls delete",
            )
            return client.labs.calls.delete(args.call_id, agency_id=agency), []

    if group == "recordings":
        if command == "list":
            return (
                client.labs.recordings.list(
                    agency_id=agency,
                    agent_key=args.agent_key,
                    call_id=args.call_id,
                    limit=args.limit,
                ),
                [],
            )
        if command == "get":
            return client.labs.recordings.get(args.recording_id, agency_id=agency), []
        if command == "delete":
            _require_confirmation(
                args.confirm,
                f"DELETE RECORDING {args.recording_id}",
                action="recordings delete",
            )
            return (
                client.labs.recordings.delete(
                    args.recording_id,
                    agency_id=agency,
                    reason=args.reason,
                ),
                [],
            )

    if group == "transcripts":
        if command == "list":
            return (
                client.labs.transcripts.list(
                    agency_id=agency,
                    agent_key=args.agent_key,
                    call_id=args.call_id,
                    limit=args.limit,
                ),
                [],
            )
        if command == "get":
            return client.labs.transcripts.get(args.transcript_id, agency_id=agency), []

    if group == "knowledge":
        if command == "status":
            return client.labs.agents.get(args.agent_id, agency_id=agency), []
        if command == "website-sync":
            return client.labs.agents.sync_knowledge(args.agent_id, {"url": args.url}), []
        if command == "website-detach":
            _require_confirmation(
                args.confirm,
                f"DETACH WEBSITE {args.agent_id}",
                action="knowledge website-detach",
            )
            return client.labs.agents.detach_website_knowledge(args.agent_id), []
        if command == "reindex":
            return client.labs.agents.reindex_knowledge(args.agent_id), []
        if command == "document-upload":
            return client.labs.agents.upload_knowledge_document(args.agent_id, args.file), []
        if command == "document-delete":
            _require_confirmation(
                args.confirm,
                f"DELETE DOCUMENT {args.document_id}",
                action="knowledge document-delete",
            )
            return (
                client.labs.agents.delete_knowledge_document(
                    args.agent_id, args.document_id
                ),
                [],
            )
        if command == "query":
            message = args.message or _read_text_file(
                str(args.message_file), label="--message-file"
            )
            history: list[dict[str, str]] = []
            if args.history_file:
                loaded = _read_json_file(str(args.history_file), label="--history-file")
                if not isinstance(loaded, list) or not all(
                    isinstance(row, Mapping) for row in loaded
                ):
                    raise CliError("--history-file must contain a JSON array of objects")
                history = [dict(row) for row in loaded]
            return (
                client.labs.agents.chat_knowledge(
                    args.agent_id, message, history=history
                ),
                [],
            )

    if group == "activity" and command == "list":
        return (
            client.labs.activity.list(
                agency_id=agency,
                event_type=args.event_type,
                resource_type=args.resource_type,
                resource_id=args.resource_id,
                limit=args.limit,
                offset=args.offset,
            ),
            [],
        )

    if group == "plans" and command == "list":
        return (
            client.labs.plans.list(
                agency_id=agency,
                resource_id=args.resource_id,
                limit=args.limit,
                offset=args.offset,
            ),
            [],
        )

    if group == "numbers":
        if command == "search":
            return (
                client.labs.phone_numbers.search(
                    {
                        "agency_id": agency,
                        "area_code": args.area_code,
                        "country_code": args.country_code,
                        "contains": args.contains,
                        "number_type": args.number_type,
                        "limit": args.limit,
                    }
                ),
                [],
            )
        if command == "pool":
            return client.labs.phone_numbers.pool(), []
        if command == "watch":
            return asyncio.run(_numbers_watch(client, args)), []
        if command == "list":
            return (
                client.labs.phone_numbers.list(
                    agency_id=agency,
                    active_only=args.active_only or None,
                ),
                [],
            )
        if command == "buy":
            return _numbers_buy(client, args), []
        if command == "assign":
            return (
                client.labs.phone_numbers.assign(
                    args.number_id,
                    {
                        "agency_id": agency,
                        "agent_key": args.agent_key,
                        "friendly_name": args.friendly_name,
                    },
                ),
                [],
            )
        if command == "unassign":
            return (
                client.labs.phone_numbers.unassign(
                    args.number_id,
                    {"agency_id": agency, "reason": args.reason},
                ),
                ["the account still owns this number; it is billed until released"],
            )
        if command == "release":
            _require_confirmation(
                args.confirm,
                f"RELEASE NUMBER {args.number_id}",
                action="numbers release",
            )
            return (
                client.labs.phone_numbers.release(
                    args.number_id,
                    {
                        "agency_id": agency,
                        "reason": args.reason,
                        "return_to_pool": not args.keep_out_of_pool,
                    },
                ),
                ["released to the carrier — the number cannot be reclaimed"],
            )

    if group == "qa":
        if command == "generate":
            prompt = args.agent_prompt or _read_text_file(
                str(args.agent_prompt_file), label="--agent-prompt-file"
            )
            return client.qa.generate(prompt, count=args.count), []
        if command in {"twin", "battle"}:
            warnings = _qa_session_login(client)
            if command == "twin":
                result = client.qa.suite(
                    count=args.count,
                    turns=args.turns,
                    supervised=args.supervised,
                )
            else:
                result = client.qa.run(scenarios=args.scenario or [], turns=args.turns)
            warnings.append(
                "free simulation: scenarios ran against the agent without carrier audio"
            )
            return result, warnings
        if command == "history":
            return client.qa.history(agent=args.agent, limit=args.limit), []
        if command == "pstn-test":
            _require_confirmation(
                args.confirm,
                f"AUTHORIZED PSTN TEST {args.to_number}",
                action="qa pstn-test",
            )
            result = client.place_call(agent_id=args.agent_id, to_number=args.to_number)
            warnings = [
                "only place PSTN tests to numbers you own or are authorized to call"
            ]
            if isinstance(result, Mapping) and result.get("simulated") is not True:
                warnings.append("billable real-audio call placed on the carrier")
            return result, warnings
        if command == "pstn-status":
            return client.labs.calls.get(args.call_id, agency_id=agency), []

    if group == "voices":
        if command == "list":
            return (
                client.labs.voices.list(
                    provider=args.provider,
                    search=args.search,
                    language=args.language,
                    cursor=args.cursor,
                    limit=args.limit,
                    agency_id=agency,
                ),
                [],
            )
        if command == "preview":
            return _voices_preview(client, args)

    if group == "campaign":
        if command == "validate":
            document = _read_text_file(args.file, label="campaign document")
            return (
                client.campaigns.validate_config(
                    document,
                    launch=True if args.assume_launch else None,
                ),
                [],
            )
        if command == "generate":
            csv = (
                _read_text_file(str(args.csv_file), label="--csv-file")
                if args.csv_file
                else None
            )
            return (
                client.campaigns.generate_config(
                    args.prompt,
                    csv=csv,
                    agent_id=args.agent_id,
                ),
                ["draft only — review it, then `supafone campaign apply` or `run`"],
            )
        if command == "apply":
            document = _read_text_file(args.file, label="campaign document")
            return client.campaigns.apply_config(document, launch=False), []
        if command == "run":
            return _campaign_run(client, args)
        if command == "status":
            return client.campaigns.stats(args.campaign_id), []

    raise CliError(f"unknown command: {group} {command}")


def _qa_session_login(client: Supafone) -> list[str]:
    """QA twin/battle are session-scoped. Log in when email+password are
    available; otherwise fall through on the API key and say so."""
    if client.email and client.password:
        client.labs_login()
        return []
    return [
        (
            "no SUPAFONE_EMAIL/SUPAFONE_PASSWORD: running key-scoped, which the "
            "Labs cloud may reject for session-scoped QA"
        )
    ]


# --------------------------------------------------------------------------
# entrypoint
# --------------------------------------------------------------------------


def _emit(result: Mapping[str, Any], output: str, stream: Any) -> None:
    if output == "text":
        print(render_text(result), file=stream)
    else:
        print(json.dumps(result, indent=2, sort_keys=True, default=str), file=stream)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command_name = f"{args.group}.{getattr(args, 'command', 'show')}"
    secrets: list[str] = []
    warnings: list[str] = []
    client: Supafone | None = None

    try:
        api_key, source = resolve_api_key(args)
        secrets = collect_secrets(api_key)
        if source == "flag:--api-key":
            warnings.append(
                "--api-key was read from the command line, where it is visible in "
                "the process table and shell history"
            )
        if args.group == "account" and args.command == "show":
            data: Any = _account_show(args, api_key, source)
        else:
            client = build_client(args, api_key)
            data, command_warnings = dispatch(client, args)
            warnings.extend(command_warnings)
    except CliError as exc:
        result = envelope(
            command_name,
            error={
                "type": "usage_error",
                "message": _scrub_text(str(exc), secrets),
                "status": None,
            },
            warnings=warnings,
        )
        _emit(result, args.output, sys.stderr)
        return EXIT_USAGE
    except PartialFailure as exc:
        result = envelope(
            command_name,
            data=redact(exc.data, secrets),
            error={
                "type": "partial_failure",
                "message": _scrub_text(str(exc), secrets),
                "status": exc.status,
                "failed_step": exc.failed_step,
                "completed_steps": exc.completed_steps,
                "remediation": exc.remediation,
            },
            warnings=warnings + _simulation_warnings(exc.data),
        )
        _emit(result, args.output, sys.stderr)
        return EXIT_PARTIAL
    except SupafoneError as exc:
        detail = exc.body.get("detail") if isinstance(exc.body, Mapping) else None
        payment: Any = None
        error_type = "api_error"
        if exc.status == 402 and isinstance(detail, Mapping):
            error_type = str(detail.get("code") or "payment_required")
            if client is not None and detail.get("checkout_endpoint"):
                try:
                    payment = client.labs.billing.top_up()
                except (
                    SupafoneError,
                    urlerror.URLError,
                    TimeoutError,
                    OSError,
                    ValueError,
                ) as checkout_exc:  # preserve the original 402
                    warnings.append(f"could not create checkout link: {checkout_exc}")
        result = envelope(
            command_name,
            data={"payment": payment, "usage": detail} if payment or detail else None,
            error={
                "type": error_type,
                "message": _scrub_text(str(exc), secrets),
                "status": exc.status,
            },
            warnings=warnings,
        )
        _emit(result, args.output, sys.stderr)
        return EXIT_API_ERROR
    except (urlerror.URLError, TimeoutError) as exc:
        # The transport never reached the API, so nothing was applied remotely —
        # but unlike a usage error this is worth retrying, so it keeps its own type.
        result = envelope(
            command_name,
            error={
                "type": "network_error",
                "message": _scrub_text(f"could not reach {args.base_url}: {exc}", secrets),
                "status": None,
            },
            warnings=warnings,
        )
        _emit(result, args.output, sys.stderr)
        return EXIT_API_ERROR
    except (OSError, ValueError) as exc:
        result = envelope(
            command_name,
            error={
                "type": "usage_error",
                "message": _scrub_text(str(exc), secrets),
                "status": None,
            },
            warnings=warnings,
        )
        _emit(result, args.output, sys.stderr)
        return EXIT_USAGE

    result = envelope(
        command_name,
        data=redact(data, secrets),
        warnings=warnings + _simulation_warnings(data),
    )
    _emit(result, args.output, sys.stdout)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
