"""The general ``supafone`` CLI — every SDK call is mocked; no network, no carrier."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from supafone_labs import cli
from supafone_labs.client import SupafoneError

API_KEY = "sl_live_abcdefghijklmnop1234"
AGENT_KEY = "agt_11111111"
NUMBER_ID = "num_22222222"
CALL_ID = "call_33333333"


# --------------------------------------------------------------------------
# fake SDK
# --------------------------------------------------------------------------


class _Namespace:
    """Records every call and replays a scripted response or raises."""

    def __init__(self, calls: list, prefix: str, responses: dict) -> None:
        self._calls = calls
        self._prefix = prefix
        self._responses = responses

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)

        def call(*args, **kwargs):
            key = f"{self._prefix}.{name}"
            self._calls.append((key, args, kwargs))
            response = self._responses.get(key, {"ok": True})
            if isinstance(response, Exception):
                raise response
            return response

        return call


class FakeClient:
    def __init__(self, responses=None, *, email="", password="") -> None:
        self.calls: list = []
        self.responses = dict(responses or {})
        self.email = email
        self.password = password
        self.labs = _Labs(self.calls, self.responses)
        self.campaigns = _Namespace(self.calls, "campaigns", self.responses)
        self.qa = _Namespace(self.calls, "qa", self.responses)

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)

        def call(*args, **kwargs):
            key = f"client.{name}"
            self.calls.append((key, args, kwargs))
            response = self.responses.get(key, {"ok": True})
            if isinstance(response, Exception):
                raise response
            return response

        return call

    def names(self) -> list[str]:
        return [entry[0] for entry in self.calls]

    def kwargs(self, key: str) -> dict:
        for name, _args, kwargs in self.calls:
            if name == key:
                return kwargs
        raise AssertionError(f"{key} was never called: {self.names()}")

    def args(self, key: str) -> tuple:
        for name, args, _kwargs in self.calls:
            if name == key:
                return args
        raise AssertionError(f"{key} was never called: {self.names()}")


class _Labs:
    def __init__(self, calls: list, responses: dict) -> None:
        self._calls = calls
        self._responses = responses
        self.agents = _Namespace(calls, "agents", responses)
        self.phone_numbers = _Namespace(calls, "phone_numbers", responses)
        self.billing = _Namespace(calls, "billing", responses)
        self.voices = _Namespace(calls, "voices", responses)
        self.tools = _Namespace(calls, "tools", responses)
        self.runtime = _Namespace(calls, "runtime", responses)
        self.telephony = _Namespace(calls, "telephony", responses)
        self.recordings = _Namespace(calls, "recordings", responses)
        self.transcripts = _Namespace(calls, "transcripts", responses)
        self.activity = _Namespace(calls, "activity", responses)
        self.plans = _Namespace(calls, "plans", responses)
        self.calls_ns = _Namespace(calls, "calls", responses)

    # `labs.calls` shadows the recorder list name, so expose it explicitly.
    @property
    def calls(self):
        return self.calls_ns

    def capabilities(self):
        self._calls.append(("labs.capabilities", (), {}))
        response = self._responses.get("labs.capabilities", {"product": "Supafone Labs"})
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in (
        "SUPAFONE_API_KEY",
        "SUPAFONE_LABS_API_KEY",
        "SUPAFONE_TOKEN",
        "SUPAFONE_ACCESS_TOKEN",
        "SUPAFONE_EMAIL",
        "SUPAFONE_PASSWORD",
        "SUPAFONE_AGENCY_ID",
        "SUPAFONE_OUTPUT",
        "SUPAFONE_API_BASE_URL",
        "SUPAFONE_LABS_API_BASE_URL",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "OPENROUTER_API_KEY",
        "GROQ_API_KEY",
        "CEREBRAS_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SUPAFONE_API_KEY", API_KEY)


def run(monkeypatch, capsys, argv, client=None):
    """Invoke the CLI with a mocked SDK client. Returns (code, envelope, raw)."""
    fake = client or FakeClient()
    monkeypatch.setattr(cli, "build_client", lambda args, api_key: fake)
    code = cli.main(argv)
    captured = capsys.readouterr()
    raw = captured.out if code == cli.EXIT_OK else captured.err
    payload = json.loads(raw) if raw.strip().startswith("{") else None
    return code, payload, raw, fake


# --------------------------------------------------------------------------
# packaging
# --------------------------------------------------------------------------


def test_console_script_installs_supafone():
    root = Path(__file__).resolve().parents[1]
    scripts = tomllib.loads((root / "pyproject.toml").read_text())["project"]["scripts"]
    assert scripts["supafone"] == "supafone_labs.cli:main"


# --------------------------------------------------------------------------
# envelope + output modes
# --------------------------------------------------------------------------


def test_json_envelope_is_stable(monkeypatch, capsys):
    code, payload, _raw, _fake = run(monkeypatch, capsys, ["capabilities"])
    assert code == cli.EXIT_OK
    assert set(payload) == {"ok", "command", "data", "error", "warnings"}
    assert payload["ok"] is True
    assert payload["command"] == "capabilities.show"
    assert payload["error"] is None
    assert payload["warnings"] == []


def test_text_mode_renders_the_same_envelope(monkeypatch, capsys):
    fake = FakeClient(
        {
            "labs.capabilities": {
                "product": "Supafone Labs",
                "runtimes": {"managed": "ultravox"},
            }
        }
    )
    code, payload, raw, _fake = run(monkeypatch, capsys, ["--output", "text", "capabilities"], fake)
    assert code == cli.EXIT_OK and payload is None
    assert raw.splitlines()[0] == "ok  capabilities.show"
    assert "product: Supafone Labs" in raw
    assert "managed: ultravox" in raw


def test_failures_go_to_stderr_with_a_stable_error_shape(monkeypatch, capsys):
    fake = FakeClient({"labs.capabilities": SupafoneError("nope", status=403)})
    code, payload, _raw, _fake = run(monkeypatch, capsys, ["capabilities"], fake)
    assert code == cli.EXIT_API_ERROR
    assert payload["ok"] is False and payload["data"] is None
    assert payload["error"] == {"type": "api_error", "message": "nope", "status": 403}


# --------------------------------------------------------------------------
# credentials
# --------------------------------------------------------------------------


def test_account_show_never_prints_the_full_key(monkeypatch, capsys):
    code, payload, raw, fake = run(monkeypatch, capsys, ["account", "show"])
    assert code == cli.EXIT_OK
    assert fake.calls == []  # no network for `account show`
    credentials = payload["data"]["credentials"]["api_key"]
    assert API_KEY not in raw
    assert credentials["masked"] == "sl_***1234"
    assert len(credentials["fingerprint"]) == 12
    assert credentials["source"] == "env:SUPAFONE_API_KEY"
    assert credentials["doubles_as_account_token"] is True


def test_account_show_masks_the_login_email_and_token(monkeypatch, capsys):
    monkeypatch.setenv("SUPAFONE_EMAIL", "ops@example.com")
    monkeypatch.setenv("SUPAFONE_PASSWORD", "hunter2-hunter2")
    monkeypatch.setenv("SUPAFONE_TOKEN", "tok_secretvalue_9999")
    _code, payload, raw, _fake = run(monkeypatch, capsys, ["account", "show"])
    assert payload["data"]["credentials"]["account_login"]["email"] == "o***@example.com"
    assert payload["data"]["credentials"]["account_token"]["masked"] == "tok***9999"
    assert "hunter2-hunter2" not in raw and "tok_secretvalue_9999" not in raw


def test_literal_api_key_flag_works_but_warns(monkeypatch, capsys):
    monkeypatch.delenv("SUPAFONE_API_KEY", raising=False)
    _code, payload, raw, _fake = run(
        monkeypatch, capsys, ["--api-key", API_KEY, "account", "show"]
    )
    assert payload["data"]["credentials"]["api_key"]["source"] == "flag:--api-key"
    assert any("process table" in warning for warning in payload["warnings"])
    assert API_KEY not in raw


def test_api_key_file_is_read_and_not_echoed(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("SUPAFONE_API_KEY", raising=False)
    key_file = tmp_path / "key.txt"
    key_file.write_text(f"{API_KEY}\n", encoding="utf-8")
    _code, payload, raw, _fake = run(
        monkeypatch, capsys, ["--api-key-file", str(key_file), "account", "show"]
    )
    assert payload["data"]["credentials"]["api_key"]["source"] == "flag:--api-key-file"
    assert payload["warnings"] == []
    assert API_KEY not in raw


def test_api_key_stdin(monkeypatch):
    import io

    args = cli.build_parser().parse_args(["--api-key-stdin", "account", "show"])
    key, source = cli.resolve_api_key(args, stdin=io.StringIO(f"{API_KEY}\n"))
    assert (key, source) == (API_KEY, "flag:--api-key-stdin")


def test_missing_key_is_a_usage_error(monkeypatch, capsys):
    monkeypatch.delenv("SUPAFONE_API_KEY", raising=False)
    code, payload, _raw, _fake = run(monkeypatch, capsys, ["capabilities"])
    assert code == cli.EXIT_USAGE
    assert payload["error"]["type"] == "usage_error"
    assert "SUPAFONE_API_KEY" in payload["error"]["message"]


def test_secrets_echoed_by_the_api_are_masked_and_scrubbed(monkeypatch, capsys):
    fake = FakeClient(
        {
            "agents.get": {
                "agent": {
                    "agent_key": AGENT_KEY,
                    "byok": {"ultravox": {"api_key": "uv_supersecret_value_1"}},
                    "twilio_auth_token": "AUTHTOKEN_abcdefgh",
                    "phone_number_sid": "PN123456789",
                    "note": f"configured with {API_KEY}",
                }
            }
        }
    )
    _code, payload, raw, _fake = run(monkeypatch, capsys, ["agents", "get", AGENT_KEY], fake)
    agent = payload["data"]["agent"]
    assert agent["byok"]["ultravox"]["api_key"] == "uv_***ue_1"
    assert agent["twilio_auth_token"] == "AUT***efgh"
    assert agent["phone_number_sid"] == "PN123456789"  # ids stay readable
    assert API_KEY not in raw and "uv_supersecret_value_1" not in raw


# --------------------------------------------------------------------------
# capabilities
# --------------------------------------------------------------------------


def test_capabilities_calls_the_sdk(monkeypatch, capsys):
    fake = FakeClient({"labs.capabilities": {"product": "Supafone Labs"}})
    _code, payload, _raw, fake = run(monkeypatch, capsys, ["capabilities"], fake)
    assert fake.names() == ["labs.capabilities"]
    assert payload["data"]["product"] == "Supafone Labs"


def test_numbers_pool_reads_only_the_explicit_shared_inventory(monkeypatch, capsys):
    fake = FakeClient(
        {
            "phone_numbers.pool": {
                "version": "developer_phone_pool_v1",
                "counts": {"total": 2, "available": 1, "in_use": 1, "unavailable": 1},
                "numbers": [
                    {"phone_number": "+14155550123", "status": "available"},
                    {"phone_number": "+14155550124", "status": "in_use"},
                ],
            }
        }
    )
    code, payload, _raw, fake = run(monkeypatch, capsys, ["numbers", "pool"], fake)
    assert code == cli.EXIT_OK
    assert fake.names() == ["phone_numbers.pool"]
    assert payload["data"]["counts"] == {
        "total": 2,
        "available": 1,
        "in_use": 1,
        "unavailable": 1,
    }


def test_account_usage_and_balance(monkeypatch, capsys):
    fake = FakeClient({"client.usage": {"oracle": 3}})
    _code, payload, _raw, fake = run(monkeypatch, capsys, ["account", "usage"], fake)
    assert fake.names() == ["client.usage"] and payload["data"] == {"oracle": 3}
    fake2 = FakeClient({"client.balance": {"minutes": 5}})
    _code, payload, _raw, fake2 = run(monkeypatch, capsys, ["account", "balance"], fake2)
    assert fake2.names() == ["client.balance"] and payload["data"] == {"minutes": 5}


def test_account_checkout_returns_a_stripe_link(monkeypatch, capsys):
    fake = FakeClient({"billing.top_up": {"url": "https://checkout.stripe.test/session"}})
    code, payload, _raw, fake = run(monkeypatch, capsys, ["account", "checkout"], fake)
    assert code == cli.EXIT_OK
    assert fake.names() == ["billing.top_up"]
    assert payload["data"]["url"].startswith("https://checkout.stripe.test/")


def test_402_returns_a_checkout_link_with_the_usage_error(monkeypatch, capsys):
    exhausted = SupafoneError(
        "managed minutes exhausted",
        status=402,
        body={
            "detail": {
                "code": "managed_minutes_exhausted",
                "checkout_endpoint": "/v1/billing/checkout",
                "minutes_remaining": 0,
            }
        },
    )
    fake = FakeClient(
        {
            "agents.get": exhausted,
            "billing.top_up": {"url": "https://checkout.stripe.test/topup"},
        }
    )
    code, payload, _raw, fake = run(
        monkeypatch, capsys, ["agents", "get", AGENT_KEY], fake
    )
    assert code == cli.EXIT_API_ERROR
    assert fake.names() == ["agents.get", "billing.top_up"]
    assert payload["error"]["type"] == "managed_minutes_exhausted"
    assert payload["data"]["payment"]["url"].endswith("/topup")
    assert payload["data"]["usage"]["minutes_remaining"] == 0


# --------------------------------------------------------------------------
# hosted agents
# --------------------------------------------------------------------------


def test_agents_create_inbound_is_the_default_direction(monkeypatch, capsys):
    fake = FakeClient({"agents.create_inbound": {"agent": {"agent_key": AGENT_KEY}}})
    code, payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["agents", "create", "--name", "Front desk", "--industry", "dental"],
        fake,
    )
    assert code == cli.EXIT_OK
    assert fake.names() == ["agents.create_inbound"]
    config = fake.args("agents.create_inbound")[0]
    assert config == {"name": "Front desk", "industry": "dental"}
    assert payload["data"]["agent"]["agent_key"] == AGENT_KEY


def test_agents_create_outbound_and_structured_flags(monkeypatch, capsys):
    fake = FakeClient({"agents.create_outbound": {"agent": {"agent_key": AGENT_KEY}}})
    _code, _payload, _raw, fake = run(
        monkeypatch,
        capsys,
        [
            "--agency-id", "acct-1",
            "agents", "create",
            "--name", "Speed to lead",
            "--direction", "outbound",
            "--voice-provider", "ultravox",
            "--voice-id", "Mark",
            "--set", "voice_watcher=true",
            "--set", "stage_count=5",
        ],
        fake,
    )
    config = fake.args("agents.create_outbound")[0]
    assert config["voice"] == {"provider": "ultravox", "voice_id": "Mark"}
    assert config["voice_watcher"] is True and config["stage_count"] == 5
    assert config["agency_id"] == "acct-1"


@pytest.mark.parametrize(
    ("provider", "env_name"),
    [
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("openai", "OPENAI_API_KEY"),
        ("gemini", "GEMINI_API_KEY"),
        ("openrouter", "OPENROUTER_API_KEY"),
        ("groq", "GROQ_API_KEY"),
        ("cerebras", "CEREBRAS_API_KEY"),
    ],
)
def test_agents_create_accepts_each_byok_supervisor_without_printing_key(
    monkeypatch, capsys, provider, env_name
):
    monkeypatch.setenv(env_name, f"{provider}-private-key")
    fake = FakeClient({"agents.create_inbound": {"agent": {"agent_key": AGENT_KEY}}})
    code, _payload, raw, fake = run(
        monkeypatch,
        capsys,
        ["agents", "create", "--name", "Desk", "--supervisor", provider],
        fake,
    )
    assert code == cli.EXIT_OK
    config = fake.args("agents.create_inbound")[0]
    assert config["supervisor"] == {
        "enabled": True,
        "mode": "byok",
        "provider": provider,
        "model": None,
        "api_key": f"{provider}-private-key",
    }
    assert f"{provider}-private-key" not in raw


def test_agents_create_byok_supervisor_requires_key_environment(monkeypatch, capsys):
    code, payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["agents", "create", "--name", "Desk", "--supervisor", "groq"],
    )
    assert code == cli.EXIT_USAGE and fake.calls == []
    assert "GROQ_API_KEY" in payload["error"]["message"]


def test_agents_create_requires_a_name(monkeypatch, capsys):
    code, payload, _raw, fake = run(monkeypatch, capsys, ["agents", "create", "--industry", "law"])
    assert code == cli.EXIT_USAGE and fake.calls == []
    assert "--name" in payload["error"]["message"]


def test_agents_create_with_number_requires_purchase_confirmation(monkeypatch, capsys):
    code, payload, _raw, fake = run(
        monkeypatch, capsys, ["agents", "create", "--name", "Desk", "--with-number"]
    )
    assert code == cli.EXIT_USAGE and fake.calls == []
    assert "--confirm-purchase" in payload["error"]["message"]


def test_agents_create_with_number_buys_after_the_agent(monkeypatch, capsys):
    fake = FakeClient(
        {
            "agents.create_inbound": {"agent": {"agent_key": AGENT_KEY}},
            "phone_numbers.buy_and_assign": {"number": {"id": NUMBER_ID, "simulated": False}},
        }
    )
    code, payload, _raw, fake = run(
        monkeypatch,
        capsys,
        [
            "agents", "create", "--name", "Desk",
            "--with-number", "--area-code", "415", "--confirm-purchase",
        ],
        fake,
    )
    assert code == cli.EXIT_OK
    assert fake.names() == ["agents.create_inbound", "phone_numbers.buy_and_assign"]
    request = fake.args("phone_numbers.buy_and_assign")[0]
    assert request["agent_key"] == AGENT_KEY
    assert request["search"] == {"area_code": "415", "limit": 1}
    assert payload["data"]["number"]["number"]["id"] == NUMBER_ID


def test_agents_create_with_number_reports_partial_failure(monkeypatch, capsys):
    fake = FakeClient(
        {
            "agents.create_inbound": {"agent": {"agent_key": AGENT_KEY}},
            "phone_numbers.buy_and_assign": SupafoneError("no numbers", status=502),
        }
    )
    code, payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["agents", "create", "--name", "Desk", "--with-number", "--confirm-purchase"],
        fake,
    )
    assert code == cli.EXIT_PARTIAL
    error = payload["error"]
    assert error["type"] == "partial_failure"
    assert error["failed_step"] == "phone_number"
    assert error["completed_steps"] == ["agent"]
    assert error["status"] == 502
    # The agent that DID land is reported, with the exact recovery commands.
    assert payload["data"]["agent_key"] == AGENT_KEY
    assert "numbers buy --agent-key agt_11111111" in error["remediation"]
    assert "agents delete agt_11111111" in error["remediation"]


def test_agents_create_with_number_partial_when_no_key_comes_back(monkeypatch, capsys):
    fake = FakeClient({"agents.create_inbound": {"agent": {"name": "Desk"}}})
    code, payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["agents", "create", "--name", "Desk", "--with-number", "--confirm-purchase"],
        fake,
    )
    assert code == cli.EXIT_PARTIAL
    assert fake.names() == ["agents.create_inbound"]
    assert payload["error"]["failed_step"] == "phone_number"


def test_agents_list_and_get(monkeypatch, capsys):
    fake = FakeClient({"agents.list": {"agents": []}})
    _code, _payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["--agency-id", "acct-1", "agents", "list", "--agent-type", "phone"],
        fake,
    )
    assert fake.kwargs("agents.list") == {"agency_id": "acct-1", "agent_type": "phone"}

    fake2 = FakeClient({"agents.get": {"agent": {"agent_key": AGENT_KEY}}})
    _code, _payload, _raw, fake2 = run(monkeypatch, capsys, ["agents", "get", AGENT_KEY], fake2)
    assert fake2.args("agents.get") == (AGENT_KEY,)
    assert fake2.kwargs("agents.get") == {"agency_id": None}


def test_agents_delete_requires_the_exact_confirmation(monkeypatch, capsys):
    code, payload, _raw, fake = run(monkeypatch, capsys, ["agents", "delete", AGENT_KEY])
    assert code == cli.EXIT_USAGE and fake.calls == []
    assert f'DELETE AGENT {AGENT_KEY}' in payload["error"]["message"]

    code, payload, _raw, fake = run(
        monkeypatch, capsys, ["agents", "delete", AGENT_KEY, "--confirm", "DELETE AGENT wrong"]
    )
    assert code == cli.EXIT_USAGE and fake.calls == []


def test_agents_delete_with_confirmation(monkeypatch, capsys):
    fake = FakeClient({"agents.delete": {"success": True, "released_number": None}})
    code, payload, _raw, fake = run(
        monkeypatch,
        capsys,
        [
            "agents", "delete", AGENT_KEY,
            "--confirm", f"DELETE AGENT {AGENT_KEY}",
            "--release-numbers",
        ],
        fake,
    )
    assert code == cli.EXIT_OK
    assert fake.kwargs("agents.delete") == {
        "agency_id": None,
        "release_numbers": True,
    }
    assert any("released to the carrier" in w for w in payload["warnings"])


# --------------------------------------------------------------------------
# hosted resource management
# --------------------------------------------------------------------------


def test_agents_update_uses_structured_fields_and_set_values(monkeypatch, capsys):
    fake = FakeClient({"agents.update": {"agent": {"agent_key": AGENT_KEY}}})
    code, _payload, _raw, fake = run(
        monkeypatch,
        capsys,
        [
            "--agency-id", "acct-1",
            "agents", "update", AGENT_KEY,
            "--greeting", "Hello",
            "--set", "tools={\"scheduling\":true}",
        ],
        fake,
    )
    assert code == cli.EXIT_OK
    assert fake.args("agents.update") == (
        AGENT_KEY,
        {"greeting": "Hello", "tools": {"scheduling": True}},
    )
    assert fake.kwargs("agents.update") == {"agency_id": "acct-1"}


def test_agents_update_accepts_json_and_requires_a_change(monkeypatch, capsys, tmp_path):
    config = tmp_path / "update.json"
    config.write_text('{"name":"After hours","language":"es"}', encoding="utf-8")
    fake = FakeClient({"agents.update": {"agent": {"agent_key": AGENT_KEY}}})
    _code, _payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["agents", "update", AGENT_KEY, "--config-file", str(config)],
        fake,
    )
    assert fake.args("agents.update")[1] == {"name": "After hours", "language": "es"}

    code, payload, _raw, fake2 = run(
        monkeypatch, capsys, ["agents", "update", AGENT_KEY]
    )
    assert code == cli.EXIT_USAGE and fake2.calls == []
    assert "requires" in payload["error"]["message"]

    code, _payload, _raw, fake3 = run(
        monkeypatch,
        capsys,
        ["--agency-id", "acct-1", "agents", "update", AGENT_KEY],
    )
    assert code == cli.EXIT_USAGE and fake3.calls == []


@pytest.mark.parametrize("command", ["readiness", "activate", "pause"])
def test_agent_lifecycle_calls_exact_sdk_method(monkeypatch, capsys, command):
    fake = FakeClient({f"agents.{command}": {"status": command}})
    code, payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["--agency-id", "acct-1", "agents", command, AGENT_KEY],
        fake,
    )
    assert code == cli.EXIT_OK
    assert fake.args(f"agents.{command}") == (AGENT_KEY,)
    assert fake.kwargs(f"agents.{command}") == {"agency_id": "acct-1"}
    assert payload["data"]["status"] == command


def test_tools_list(monkeypatch, capsys):
    fake = FakeClient({"tools.list": {"tools": [{"name": "route_call"}]}})
    code, payload, _raw, fake = run(monkeypatch, capsys, ["tools", "list"], fake)
    assert code == cli.EXIT_OK
    assert fake.names() == ["tools.list"]
    assert payload["data"]["tools"][0]["name"] == "route_call"


def test_runtime_get_and_update_credentials_are_file_only_and_redacted(
    monkeypatch, capsys, tmp_path
):
    fake = FakeClient({"runtime.get": {"provider": "ultravox", "configured": True}})
    _code, _payload, _raw, fake = run(
        monkeypatch, capsys, ["--agency-id", "acct-1", "runtime", "get"], fake
    )
    assert fake.kwargs("runtime.get") == {"agency_id": "acct-1"}

    secret = "runtime-private-secret-1234"
    credentials = tmp_path / "runtime.json"
    credentials.write_text(json.dumps({"api_key": secret}), encoding="utf-8")
    fake2 = FakeClient(
        {"runtime.configure": {"provider": "ultravox", "credentials": {"api_key": secret}}}
    )
    code, payload, raw, fake2 = run(
        monkeypatch,
        capsys,
        [
            "--agency-id", "acct-1", "runtime", "update",
            "--provider", "ultravox", "--credentials-file", str(credentials),
        ],
        fake2,
    )
    assert code == cli.EXIT_OK
    assert fake2.args("runtime.configure")[0] == {
        "agency_id": "acct-1",
        "provider": "ultravox",
        "credentials": {"api_key": secret},
    }
    assert secret not in raw
    assert payload["data"]["credentials"]["api_key"] == "run***1234"


def test_telephony_get_and_update_managed_or_byok(monkeypatch, capsys, tmp_path):
    fake = FakeClient({"telephony.get": {"mode": "supafone_managed"}})
    _code, _payload, _raw, fake = run(
        monkeypatch, capsys, ["telephony", "get"], fake
    )
    assert fake.kwargs("telephony.get") == {"agency_id": None}

    credentials = tmp_path / "carrier.json"
    credentials.write_text('{"account_sid":"AC1","auth_token":"carrier-secret"}')
    fake2 = FakeClient({"telephony.configure": {"configured": True}})
    _code, _payload, _raw, fake2 = run(
        monkeypatch,
        capsys,
        [
            "telephony", "update", "--mode", "byok", "--provider", "twilio",
            "--credentials-file", str(credentials),
        ],
        fake2,
    )
    assert fake2.args("telephony.configure")[0] == {
        "mode": "byok",
        "provider": "twilio",
        "credentials": {"account_sid": "AC1", "auth_token": "carrier-secret"},
    }


def test_calls_list_and_get_use_durable_call_namespace(monkeypatch, capsys):
    fake = FakeClient({"calls.list": {"calls": []}})
    _code, _payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["calls", "list", "--agent-key", AGENT_KEY, "--limit", "12", "--offset", "4"],
        fake,
    )
    assert fake.kwargs("calls.list") == {
        "agency_id": None,
        "agent_key": AGENT_KEY,
        "limit": 12,
        "offset": 4,
    }
    fake2 = FakeClient({"calls.get": {"call_id": CALL_ID}})
    _code, payload, _raw, fake2 = run(
        monkeypatch, capsys, ["calls", "get", CALL_ID], fake2
    )
    assert fake2.args("calls.get") == (CALL_ID,)
    assert payload["data"]["call_id"] == CALL_ID


def test_calls_delete_requires_exact_confirmation(monkeypatch, capsys):
    code, payload, _raw, fake = run(monkeypatch, capsys, ["calls", "delete", CALL_ID])
    assert code == cli.EXIT_USAGE and fake.calls == []
    assert f"DELETE CALL {CALL_ID}" in payload["error"]["message"]

    fake2 = FakeClient({"calls.delete": {"deleted": True}})
    code, _payload, _raw, fake2 = run(
        monkeypatch,
        capsys,
        ["calls", "delete", CALL_ID, "--confirm", f"DELETE CALL {CALL_ID}"],
        fake2,
    )
    assert code == cli.EXIT_OK
    assert fake2.args("calls.delete") == (CALL_ID,)


def test_recordings_list_get_and_confirmed_delete(monkeypatch, capsys):
    fake = FakeClient({"recordings.list": {"recordings": []}})
    _code, _payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["recordings", "list", "--agent-key", AGENT_KEY, "--call-id", CALL_ID],
        fake,
    )
    assert fake.kwargs("recordings.list") == {
        "agency_id": None,
        "agent_key": AGENT_KEY,
        "call_id": CALL_ID,
        "limit": 50,
    }
    fake2 = FakeClient({"recordings.get": {"recording_id": "rec-1"}})
    _code, _payload, _raw, fake2 = run(
        monkeypatch, capsys, ["recordings", "get", "rec-1"], fake2
    )
    assert fake2.args("recordings.get") == ("rec-1",)

    code, _payload, _raw, fake3 = run(
        monkeypatch, capsys, ["recordings", "delete", "rec-1"]
    )
    assert code == cli.EXIT_USAGE and fake3.calls == []
    fake4 = FakeClient({"recordings.delete": {"deleted": True}})
    _code, _payload, _raw, fake4 = run(
        monkeypatch,
        capsys,
        [
            "recordings", "delete", "rec-1", "--reason", "retention",
            "--confirm", "DELETE RECORDING rec-1",
        ],
        fake4,
    )
    assert fake4.kwargs("recordings.delete") == {
        "agency_id": None,
        "reason": "retention",
    }


def test_transcripts_list_and_get(monkeypatch, capsys):
    fake = FakeClient({"transcripts.list": {"transcripts": []}})
    _code, _payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["transcripts", "list", "--call-id", CALL_ID, "--limit", "9"],
        fake,
    )
    assert fake.kwargs("transcripts.list") == {
        "agency_id": None,
        "agent_key": None,
        "call_id": CALL_ID,
        "limit": 9,
    }
    fake2 = FakeClient({"transcripts.get": {"transcript_id": "tr-1"}})
    _code, _payload, _raw, fake2 = run(
        monkeypatch, capsys, ["transcripts", "get", "tr-1"], fake2
    )
    assert fake2.args("transcripts.get") == ("tr-1",)


def test_knowledge_status_sync_reindex_and_upload(monkeypatch, capsys, tmp_path):
    fake = FakeClient({"agents.get": {"agent": {"knowledge_status": "ready"}}})
    _code, payload, _raw, fake = run(
        monkeypatch, capsys, ["knowledge", "status", AGENT_KEY], fake
    )
    assert fake.args("agents.get") == (AGENT_KEY,)
    assert payload["data"]["agent"]["knowledge_status"] == "ready"

    fake2 = FakeClient({"agents.sync_knowledge": {"status": "queued"}})
    _code, _payload, _raw, fake2 = run(
        monkeypatch,
        capsys,
        ["knowledge", "website-sync", AGENT_KEY, "--url", "https://example.com"],
        fake2,
    )
    assert fake2.args("agents.sync_knowledge") == (
        AGENT_KEY,
        {"url": "https://example.com"},
    )

    fake3 = FakeClient({"agents.reindex_knowledge": {"status": "queued"}})
    _code, _payload, _raw, fake3 = run(
        monkeypatch, capsys, ["knowledge", "reindex", AGENT_KEY], fake3
    )
    assert fake3.args("agents.reindex_knowledge") == (AGENT_KEY,)

    document = tmp_path / "faq.md"
    document.write_text("# FAQ", encoding="utf-8")
    fake4 = FakeClient({"agents.upload_knowledge_document": {"document_id": "doc-1"}})
    _code, _payload, _raw, fake4 = run(
        monkeypatch,
        capsys,
        ["knowledge", "document-upload", AGENT_KEY, str(document)],
        fake4,
    )
    assert fake4.args("agents.upload_knowledge_document") == (AGENT_KEY, str(document))


def test_knowledge_destructive_operations_require_confirmation(monkeypatch, capsys):
    code, _payload, _raw, fake = run(
        monkeypatch, capsys, ["knowledge", "website-detach", AGENT_KEY]
    )
    assert code == cli.EXIT_USAGE and fake.calls == []
    fake2 = FakeClient({"agents.detach_website_knowledge": {"detached": True}})
    _code, _payload, _raw, fake2 = run(
        monkeypatch,
        capsys,
        [
            "knowledge", "website-detach", AGENT_KEY,
            "--confirm", f"DETACH WEBSITE {AGENT_KEY}",
        ],
        fake2,
    )
    assert fake2.args("agents.detach_website_knowledge") == (AGENT_KEY,)

    code, _payload, _raw, fake3 = run(
        monkeypatch, capsys, ["knowledge", "document-delete", AGENT_KEY, "doc-1"]
    )
    assert code == cli.EXIT_USAGE and fake3.calls == []
    fake4 = FakeClient({"agents.delete_knowledge_document": {"deleted": True}})
    _code, _payload, _raw, fake4 = run(
        monkeypatch,
        capsys,
        [
            "knowledge", "document-delete", AGENT_KEY, "doc-1",
            "--confirm", "DELETE DOCUMENT doc-1",
        ],
        fake4,
    )
    assert fake4.args("agents.delete_knowledge_document") == (AGENT_KEY, "doc-1")


def test_knowledge_query_supports_message_file_and_validated_history(
    monkeypatch, capsys, tmp_path
):
    message = tmp_path / "question.txt"
    message.write_text("What are your hours?", encoding="utf-8")
    history = tmp_path / "history.json"
    history.write_text('[{"role":"user","content":"Hello"}]', encoding="utf-8")
    fake = FakeClient({"agents.chat_knowledge": {"answer": "Nine to five."}})
    _code, payload, _raw, fake = run(
        monkeypatch,
        capsys,
        [
            "knowledge", "query", AGENT_KEY, "--message-file", str(message),
            "--history-file", str(history),
        ],
        fake,
    )
    assert fake.args("agents.chat_knowledge") == (AGENT_KEY, "What are your hours?")
    assert fake.kwargs("agents.chat_knowledge") == {
        "history": [{"role": "user", "content": "Hello"}]
    }
    assert payload["data"]["answer"] == "Nine to five."

    history.write_text('{"not":"an array"}', encoding="utf-8")
    code, error_payload, _raw, fake2 = run(
        monkeypatch,
        capsys,
        [
            "knowledge", "query", AGENT_KEY, "--message", "Question",
            "--history-file", str(history),
        ],
    )
    assert code == cli.EXIT_USAGE and fake2.calls == []
    assert "JSON array" in error_payload["error"]["message"]


def test_activity_and_plans_list_forward_filters(monkeypatch, capsys):
    fake = FakeClient({"activity.list": {"events": []}})
    _code, _payload, _raw, fake = run(
        monkeypatch,
        capsys,
        [
            "--agency-id", "acct-1", "activity", "list",
            "--event-type", "call.completed", "--resource-type", "call",
            "--resource-id", CALL_ID, "--limit", "8", "--offset", "2",
        ],
        fake,
    )
    assert fake.kwargs("activity.list") == {
        "agency_id": "acct-1",
        "event_type": "call.completed",
        "resource_type": "call",
        "resource_id": CALL_ID,
        "limit": 8,
        "offset": 2,
    }

    fake2 = FakeClient({"plans.list": {"events": []}})
    _code, _payload, _raw, fake2 = run(
        monkeypatch,
        capsys,
        ["plans", "list", "--resource-id", "plan-1", "--limit", "7"],
        fake2,
    )
    assert fake2.kwargs("plans.list") == {
        "agency_id": None,
        "resource_id": "plan-1",
        "limit": 7,
        "offset": 0,
    }


# --------------------------------------------------------------------------
# managed numbers
# --------------------------------------------------------------------------


def test_numbers_search_passes_the_documented_filters(monkeypatch, capsys):
    fake = FakeClient({"phone_numbers.search": {"simulated": True, "numbers": []}})
    _code, payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["numbers", "search", "--area-code", "415", "--limit", "3"],
        fake,
    )
    assert fake.args("phone_numbers.search")[0] == {
        "agency_id": None,
        "area_code": "415",
        "country_code": "US",
        "contains": None,
        "number_type": None,
        "limit": 3,
    }
    assert any("simulated" in warning for warning in payload["warnings"])


def test_numbers_list_active_only(monkeypatch, capsys):
    fake = FakeClient({"phone_numbers.list": {"numbers": []}})
    _code, _payload, _raw, fake = run(
        monkeypatch, capsys, ["numbers", "list", "--active-only"], fake
    )
    assert fake.kwargs("phone_numbers.list") == {"agency_id": None, "active_only": True}


def test_numbers_buy_requires_purchase_confirmation(monkeypatch, capsys):
    code, payload, _raw, fake = run(
        monkeypatch, capsys, ["numbers", "buy", "--agent-key", AGENT_KEY]
    )
    assert code == cli.EXIT_USAGE and fake.calls == []
    assert "--confirm-purchase" in payload["error"]["message"]


def test_numbers_buy_with_confirmation(monkeypatch, capsys):
    fake = FakeClient(
        {"phone_numbers.buy_and_assign": {"number": {"id": NUMBER_ID, "simulated": False}}}
    )
    code, payload, _raw, fake = run(
        monkeypatch,
        capsys,
        [
            "numbers", "buy",
            "--agent-key", AGENT_KEY,
            "--phone-number", "+14155550123",
            "--confirm-purchase",
        ],
        fake,
    )
    assert code == cli.EXIT_OK
    assert fake.args("phone_numbers.buy_and_assign")[0] == {
        "agent_key": AGENT_KEY,
        "phone_number": "+14155550123",
    }
    assert payload["warnings"] == ["real carrier action: this was billable"]


def test_numbers_assign_and_unassign(monkeypatch, capsys):
    fake = FakeClient({"phone_numbers.assign": {"number": {"id": NUMBER_ID}}})
    _code, _payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["numbers", "assign", NUMBER_ID, "--agent-key", AGENT_KEY],
        fake,
    )
    assert fake.args("phone_numbers.assign") == (
        NUMBER_ID,
        {"agency_id": None, "agent_key": AGENT_KEY, "friendly_name": None},
    )

    fake2 = FakeClient({"phone_numbers.unassign": {"success": True}})
    _code, payload, _raw, fake2 = run(
        monkeypatch, capsys, ["numbers", "unassign", NUMBER_ID], fake2
    )
    assert fake2.args("phone_numbers.unassign")[0] == NUMBER_ID
    assert any("still owns this number" in w for w in payload["warnings"])


def test_numbers_release_requires_the_exact_confirmation(monkeypatch, capsys):
    code, payload, _raw, fake = run(monkeypatch, capsys, ["numbers", "release", NUMBER_ID])
    assert code == cli.EXIT_USAGE and fake.calls == []
    assert f"RELEASE NUMBER {NUMBER_ID}" in payload["error"]["message"]


def test_numbers_release_with_confirmation_returns_to_pool_by_default(monkeypatch, capsys):
    fake = FakeClient({"phone_numbers.release": {"success": True}})
    code, payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["numbers", "release", NUMBER_ID, "--confirm", f"RELEASE NUMBER {NUMBER_ID}"],
        fake,
    )
    assert code == cli.EXIT_OK
    assert fake.args("phone_numbers.release")[1]["return_to_pool"] is True
    assert any("cannot be reclaimed" in w for w in payload["warnings"])

    fake2 = FakeClient({"phone_numbers.release": {"success": True}})
    _code, _payload, _raw, fake2 = run(
        monkeypatch,
        capsys,
        [
            "numbers", "release", NUMBER_ID,
            "--confirm", f"RELEASE NUMBER {NUMBER_ID}",
            "--keep-out-of-pool",
        ],
        fake2,
    )
    assert fake2.args("phone_numbers.release")[1]["return_to_pool"] is False


# --------------------------------------------------------------------------
# QA
# --------------------------------------------------------------------------


def test_qa_generate_from_a_prompt_file(monkeypatch, capsys, tmp_path):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("You are an intake agent.", encoding="utf-8")
    fake = FakeClient({"qa.generate": {"scenarios": []}})
    _code, _payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["qa", "generate", "--agent-prompt-file", str(prompt_file), "--count", "3"],
        fake,
    )
    assert fake.args("qa.generate") == ("You are an intake agent.",)
    assert fake.kwargs("qa.generate") == {"count": 3}


def test_qa_twin_logs_in_and_is_free_simulation(monkeypatch, capsys):
    monkeypatch.setenv("SUPAFONE_EMAIL", "ops@example.com")
    monkeypatch.setenv("SUPAFONE_PASSWORD", "hunter2-hunter2")
    fake = FakeClient({"qa.suite": {"summary": {}}}, email="ops@example.com", password="pw")
    code, payload, _raw, fake = run(
        monkeypatch, capsys, ["qa", "twin", "--count", "6", "--turns", "3", "--supervised"], fake
    )
    assert code == cli.EXIT_OK
    assert fake.names() == ["client.labs_login", "qa.suite"]
    assert fake.kwargs("qa.suite") == {"count": 6, "turns": 3, "supervised": True}
    assert any("free simulation" in w for w in payload["warnings"])
    assert not any("billable" in w for w in payload["warnings"])


def test_qa_battle_runs_the_ab_arms(monkeypatch, capsys):
    fake = FakeClient({"qa.run": {"lift": 0.2}}, email="ops@example.com", password="pw")
    _code, payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["qa", "battle", "--scenario", "refund_bully", "--scenario", "angry", "--turns", "4"],
        fake,
    )
    assert fake.kwargs("qa.run") == {"scenarios": ["refund_bully", "angry"], "turns": 4}
    assert any("free simulation" in w for w in payload["warnings"])


def test_qa_battle_without_login_warns_but_still_runs(monkeypatch, capsys):
    fake = FakeClient({"qa.run": {"lift": 0.1}})
    _code, payload, _raw, fake = run(monkeypatch, capsys, ["qa", "battle"], fake)
    assert "client.labs_login" not in fake.names()
    assert any("key-scoped" in w for w in payload["warnings"])


def test_qa_history(monkeypatch, capsys):
    fake = FakeClient({"qa.history": {"runs": []}})
    _code, _payload, _raw, fake = run(
        monkeypatch, capsys, ["qa", "history", "--agent", "intake", "--limit", "10"], fake
    )
    assert fake.kwargs("qa.history") == {"agent": "intake", "limit": 10}


def test_qa_pstn_test_requires_the_exact_authorization(monkeypatch, capsys):
    code, payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["qa", "pstn-test", "--agent-id", "a1", "--to", "+14155550123"],
        FakeClient(),
    )
    assert code == cli.EXIT_USAGE and fake.calls == []
    assert "AUTHORIZED PSTN TEST +14155550123" in payload["error"]["message"]

    # A confirmation naming a DIFFERENT number must not authorize this dial.
    code, _payload, _raw, fake = run(
        monkeypatch,
        capsys,
        [
            "qa", "pstn-test", "--agent-id", "a1", "--to", "+14155550123",
            "--confirm", "AUTHORIZED PSTN TEST +14155559999",
        ],
        FakeClient(),
    )
    assert code == cli.EXIT_USAGE and fake.calls == []


def test_qa_pstn_test_real_audio_is_flagged_billable(monkeypatch, capsys):
    fake = FakeClient(
        {
            "client.place_call": {
                "success": True,
                "simulated": False,
                "call_record_id": CALL_ID,
                "provider": "native",
            }
        }
    )
    code, payload, _raw, fake = run(
        monkeypatch,
        capsys,
        [
            "qa", "pstn-test", "--agent-id", "a1", "--to", "+14155550123",
            "--confirm", "AUTHORIZED PSTN TEST +14155550123",
        ],
        fake,
    )
    assert code == cli.EXIT_OK
    assert fake.kwargs("client.place_call") == {"agent_id": "a1", "to_number": "+14155550123"}
    assert any("billable real-audio" in w for w in payload["warnings"])
    assert any("authorized to call" in w for w in payload["warnings"])


def test_qa_pstn_test_simulated_is_flagged_free(monkeypatch, capsys):
    fake = FakeClient(
        {"client.place_call": {"success": True, "simulated": True, "call_record_id": CALL_ID}}
    )
    _code, payload, _raw, _fake = run(
        monkeypatch,
        capsys,
        [
            "qa", "pstn-test", "--agent-id", "a1", "--to", "+14155550123",
            "--confirm", "AUTHORIZED PSTN TEST +14155550123",
        ],
        fake,
    )
    assert not any("billable" in w for w in payload["warnings"])
    assert any("nothing was billed" in w for w in payload["warnings"])


def test_qa_pstn_status_reads_the_call_record(monkeypatch, capsys):
    fake = FakeClient({"calls.get": {"call": {"id": CALL_ID, "status": "completed"}}})
    _code, payload, _raw, fake = run(monkeypatch, capsys, ["qa", "pstn-status", CALL_ID], fake)
    assert fake.args("calls.get") == (CALL_ID,)
    assert payload["data"]["call"]["status"] == "completed"


# --------------------------------------------------------------------------
# voices
# --------------------------------------------------------------------------


def test_voices_list_filters(monkeypatch, capsys):
    fake = FakeClient({"voices.list": {"voices": []}})
    _code, _payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["voices", "list", "--provider", "cartesia", "--search", "calm", "--limit", "10"],
        fake,
    )
    assert fake.kwargs("voices.list") == {
        "provider": "cartesia",
        "search": "calm",
        "language": None,
        "cursor": None,
        "limit": 10,
        "agency_id": None,
    }


def test_voices_preview_returns_metadata_only(monkeypatch, capsys):
    fake = FakeClient(
        {
            "voices.list": {
                "voices": [
                    {"id": "other", "preview_url": "https://x/other.mp3"},
                    {
                        "id": "Mark",
                        "provider": "ultravox",
                        "language": "en",
                        "preview_url": "https://x/mark.mp3",
                    },
                ]
            }
        }
    )
    code, payload, _raw, fake = run(monkeypatch, capsys, ["voices", "preview", "Mark"], fake)
    assert code == cli.EXIT_OK
    assert fake.names() == ["voices.list"]  # metadata only: no audio call
    preview = payload["data"]["preview"]
    assert preview["preview_url"] == "https://x/mark.mp3"
    assert preview["audio_downloaded"] is False
    assert preview["endpoint"].endswith("/api/v1/labs/voices/preview?voice=Mark")
    assert payload["data"]["voice"]["provider"] == "ultravox"


def test_voices_preview_unknown_voice_is_a_usage_error(monkeypatch, capsys):
    fake = FakeClient({"voices.list": {"voices": []}})
    code, payload, _raw, _fake = run(monkeypatch, capsys, ["voices", "preview", "Nope"], fake)
    assert code == cli.EXIT_USAGE
    assert "not in this account's catalog" in payload["error"]["message"]


def test_voices_preview_warns_when_no_preview_audio_exists(monkeypatch, capsys):
    fake = FakeClient({"voices.list": {"voices": [{"id": "Mark", "preview_url": None}]}})
    _code, payload, _raw, _fake = run(monkeypatch, capsys, ["voices", "preview", "Mark"], fake)
    assert any("no preview audio URL" in w for w in payload["warnings"])


# --------------------------------------------------------------------------
# campaigns
# --------------------------------------------------------------------------


def test_campaign_validate_has_no_side_effects(monkeypatch, capsys, tmp_path):
    doc = tmp_path / "campaign.yaml"
    doc.write_text("slug: winback\n", encoding="utf-8")
    fake = FakeClient({"campaigns.validate_config": {"valid": True, "errors": []}})
    code, payload, _raw, fake = run(
        monkeypatch, capsys, ["campaign", "validate", str(doc)], fake
    )
    assert code == cli.EXIT_OK
    assert fake.names() == ["campaigns.validate_config"]
    assert fake.args("campaigns.validate_config") == ("slug: winback\n",)
    assert fake.kwargs("campaigns.validate_config") == {"launch": None}
    assert payload["data"]["valid"] is True


def test_campaign_validate_assume_launch(monkeypatch, capsys, tmp_path):
    doc = tmp_path / "campaign.yaml"
    doc.write_text("slug: winback\n", encoding="utf-8")
    fake = FakeClient({"campaigns.validate_config": {"valid": True}})
    run(monkeypatch, capsys, ["campaign", "validate", str(doc), "--assume-launch"], fake)
    assert fake.kwargs("campaigns.validate_config") == {"launch": True}


def test_campaign_generate_is_a_draft(monkeypatch, capsys, tmp_path):
    csv = tmp_path / "leads.csv"
    csv.write_text("name,phone\n", encoding="utf-8")
    fake = FakeClient({"campaigns.generate_config": {"config": "slug: x"}})
    _code, payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["campaign", "generate", "Win back lapsed patients", "--csv-file", str(csv)],
        fake,
    )
    assert fake.args("campaigns.generate_config") == ("Win back lapsed patients",)
    assert fake.kwargs("campaigns.generate_config") == {"csv": "name,phone\n", "agent_id": None}
    assert any("draft only" in w for w in payload["warnings"])


def test_campaign_apply_does_not_launch(monkeypatch, capsys, tmp_path):
    doc = tmp_path / "campaign.yaml"
    doc.write_text("slug: winback\n", encoding="utf-8")
    fake = FakeClient({"campaigns.apply_config": {"campaign": {"id": "c1"}}})
    _code, payload, _raw, fake = run(monkeypatch, capsys, ["campaign", "apply", str(doc)], fake)
    assert fake.kwargs("campaigns.apply_config") == {"launch": False}
    assert payload["warnings"] == []


def test_campaign_run_requires_confirmation(monkeypatch, capsys, tmp_path):
    doc = tmp_path / "campaign.yaml"
    doc.write_text("slug: winback\n", encoding="utf-8")
    code, payload, _raw, fake = run(
        monkeypatch,
        capsys,
        ["campaign", "run", str(doc)],
        FakeClient(),
    )
    assert code == cli.EXIT_USAGE and fake.calls == []
    assert '--confirm "LAUNCH"' in payload["error"]["message"]


def test_campaign_run_validates_before_handing_off(monkeypatch, capsys, tmp_path):
    doc = tmp_path / "campaign.yaml"
    doc.write_text("slug: winback\n", encoding="utf-8")
    fake = FakeClient(
        {
            "campaigns.validate_config": {"valid": True},
            "campaigns.apply_config": {"campaign": {"id": "c1"}, "launched": True},
        }
    )
    code, payload, _raw, fake = run(
        monkeypatch, capsys, ["campaign", "run", str(doc), "--confirm", "LAUNCH"], fake
    )
    assert code == cli.EXIT_OK
    assert fake.names() == ["campaigns.validate_config", "campaigns.apply_config"]
    assert fake.kwargs("campaigns.apply_config") == {"launch": True}
    assert payload["data"]["handoff"]["launched"] is True
    assert any("real outbound calls" in w for w in payload["warnings"])


def test_campaign_run_stops_on_invalid_documents(monkeypatch, capsys, tmp_path):
    doc = tmp_path / "campaign.yaml"
    doc.write_text("slug: winback\n", encoding="utf-8")
    fake = FakeClient(
        {"campaigns.validate_config": {"valid": False, "errors": ["missing agent_id"]}}
    )
    code, payload, _raw, fake = run(
        monkeypatch, capsys, ["campaign", "run", str(doc), "--confirm", "LAUNCH"], fake
    )
    assert code == cli.EXIT_USAGE
    assert fake.names() == ["campaigns.validate_config"]  # never applied
    assert "missing agent_id" in payload["error"]["message"]


def test_campaign_run_reports_partial_failure_after_validation(monkeypatch, capsys, tmp_path):
    doc = tmp_path / "campaign.yaml"
    doc.write_text("slug: winback\n", encoding="utf-8")
    fake = FakeClient(
        {
            "campaigns.validate_config": {"valid": True},
            "campaigns.apply_config": SupafoneError("quota exhausted", status=402),
        }
    )
    code, payload, _raw, _fake = run(
        monkeypatch, capsys, ["campaign", "run", str(doc), "--confirm", "LAUNCH"], fake
    )
    assert code == cli.EXIT_PARTIAL
    assert payload["error"]["failed_step"] == "launch"
    assert payload["error"]["completed_steps"] == ["validate"]
    assert payload["error"]["status"] == 402
    assert "no calls were started" in payload["error"]["remediation"]


def test_campaign_status(monkeypatch, capsys):
    fake = FakeClient({"campaigns.stats": {"dialed": 12}})
    _code, payload, _raw, fake = run(monkeypatch, capsys, ["campaign", "status", "c1"], fake)
    assert fake.args("campaigns.stats") == ("c1",)
    assert payload["data"]["dialed"] == 12


# --------------------------------------------------------------------------
# unit-level helpers
# --------------------------------------------------------------------------


def test_redact_leaves_non_secret_shapes_alone():
    payload = {
        "api_key_present": True,
        "token_count": 4,
        "secret": "",
        "nested": [{"password": "correct horse battery"}],
    }
    out = cli.redact(payload)
    assert out["api_key_present"] is True
    assert out["token_count"] == 4
    assert out["secret"] == ""
    assert out["nested"][0]["password"] == "cor***tery"


def test_simulation_warnings_distinguish_modes():
    assert cli._simulation_warnings({"simulated": True})[0].startswith("simulated:")
    assert cli._simulation_warnings({"simulated": False}) == [
        "real carrier action: this was billable"
    ]
    mixed = cli._simulation_warnings({"a": {"simulated": True}, "b": {"simulated": False}})
    assert mixed == ["mixed simulated and real carrier results — check `simulated` per record"]
    assert cli._simulation_warnings({"status": "ok"}) == []


def test_parse_set_rejects_malformed_pairs():
    assert cli._parse_set(["a=1", "b=text", 'c={"k": 1}']) == {"a": 1, "b": "text", "c": {"k": 1}}
    with pytest.raises(cli.CliError):
        cli._parse_set(["nope"])


def test_unreachable_api_is_a_network_error_not_a_usage_error(monkeypatch, capsys):
    import urllib.error

    fake = FakeClient({"labs.capabilities": urllib.error.URLError("Connection refused")})
    code, payload, _raw, _fake = run(monkeypatch, capsys, ["capabilities"], fake)
    assert code == cli.EXIT_API_ERROR
    assert payload["error"]["type"] == "network_error"
    assert payload["error"]["status"] is None
    assert "https://api.supafone.ai" in payload["error"]["message"]


def test_network_error_scrubs_credentials_from_the_url(monkeypatch, capsys):
    import urllib.error

    fake = FakeClient({"labs.capabilities": urllib.error.URLError(f"denied for {API_KEY}")})
    _code, _payload, raw, _fake = run(monkeypatch, capsys, ["capabilities"], fake)
    assert API_KEY not in raw
