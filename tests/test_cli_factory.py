"""CLI-to-SDK contract checks with a recording transport, never a live API."""

from __future__ import annotations

import json
import os
from importlib.metadata import version
from urllib.parse import parse_qs, urlsplit

import pytest

from supafone_labs import Supafone, cli
from supafone_labs.client import SupafoneError


@pytest.fixture
def invoke(monkeypatch, capsys):
    for name in tuple(os.environ):
        if name.startswith("SUPAFONE_") or name in cli.SUPERVISOR_KEY_ENVS.values():
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SUPAFONE_API_KEY", "sf_test_cli_factory")
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True}

    client = Supafone(api_key="sf_test_cli_factory", transport=transport)
    monkeypatch.setattr(cli, "build_client", lambda *_: client)

    def run(argv):
        code = cli.main(argv)
        output = capsys.readouterr()
        raw = output.out if code == cli.EXIT_OK else output.err
        return code, json.loads(raw), calls

    return run


@pytest.mark.parametrize("alias,provider", [
    ("openai", "openai"), ("google", "google"), ("gemini", "google"),
    ("xai", "xai"), ("grok", "xai"), ("smallest", "smallest"),
    ("hydra", "smallest"),
])
def test_native_provider_aliases_use_the_real_sdk(invoke, alias, provider):
    code, _, calls = invoke([
        "agents", "create", "--name", "Front desk", "--s2s-provider", alias,
        "--s2s-model", "catalog-model", "--s2s-voice", "catalog-voice",
        "--manager", "managed", "--supervisor", "managed", "--stage-count", "3",
    ])
    assert code == cli.EXIT_OK
    assert len(calls) == 1
    method, path, body = calls[0]
    assert (method, path) == ("POST", "/api/v1/labs/agents")
    assert body["realtime"] == {
        "provider": provider, "model": "catalog-model", "voice": "catalog-voice",
    }
    assert body["manager"] == {"enabled": True, "reasoning": "managed"}
    assert body["supervisor"]["mode"] == "managed"
    assert body["stage_count"] == 3


def test_ultravox_reset_patch_has_no_creation_defaults(invoke):
    code, _, calls = invoke([
        "agents", "update", "front-desk", "--s2s-provider", "ultravox",
        "--manager", "off", "--supervisor", "off",
    ])
    assert code == cli.EXIT_OK
    assert calls == [("PATCH", "/api/v1/labs/agents/front-desk", {
        "realtime": None, "manager": False, "voice_watcher": False,
    })]


def test_ultravox_create_can_select_custom_tts(invoke):
    code, _, calls = invoke([
        "agents", "create", "--name", "Desk", "--s2s-provider", "ultravox",
        "--voice-provider", "cartesia", "--voice-id", "catalog-voice",
    ])
    assert code == cli.EXIT_OK
    assert calls[0][2].get("realtime") is None
    assert calls[0][2]["voice"] == {"provider": "cartesia", "voice_id": "catalog-voice"}


def test_manager_can_reuse_supervisor_profile(invoke):
    code, _, calls = invoke(["agents", "update", "desk", "--manager", "supervisor"])
    assert code == cli.EXIT_OK
    assert calls[0][2] == {"manager": {"enabled": True, "reasoning": "supervisor"}}


@pytest.mark.parametrize("provider,expected", [
    ("gemini", {"provider": "google", "model": "saved-model", "voice": "saved-voice"}),
    ("grok", {"provider": "xai"}),
])
def test_provider_switch_keeps_only_compatible_saved_selection(invoke, tmp_path, provider, expected):
    config = tmp_path / "agent.json"
    config.write_text(json.dumps({"realtime": {
        "provider": "google", "model": "saved-model", "voice": "saved-voice",
    }}))
    code, _, calls = invoke([
        "agents", "update", "desk", "--config-file", str(config), "--s2s-provider", provider,
    ])
    assert code == cli.EXIT_OK
    assert calls[0][2] == {"realtime": expected}


def test_factory_config_preserves_gates_teams_and_explicit_empty_lists(invoke, tmp_path):
    config = tmp_path / "factory.json"
    config.write_text(json.dumps({
        "captureFields": ["name"],
        "manager": {"enabled": True, "maxTasks": 6, "maxParallel": 2},
        "agentTeam": {"enabled": True, "members": [
            {"id": "scheduler", "stageKeys": ["book"], "tools": []},
        ]},
        "callStages": [
            {"key": "capture", "tools": ["save_lead"], "nextStages": ["book"],
             "requirements": {"requiredFields": ["name"], "successfulTools": []}},
            {"key": "book", "tools": ["book_appointment"], "nextStages": ["confirm"],
             "specialistId": "scheduler", "requirements": {"successfulTools": ["book_appointment"]}},
            {"key": "confirm", "tools": [], "nextStages": []},
        ],
        "runtimeRouting": {"enabled": False, "allowedModels": []},
        "recording": False,
    }))
    code, _, calls = invoke(["agents", "update", "desk", "--config-file", str(config)])
    assert code == cli.EXIT_OK
    body = calls[0][2]
    assert body["capture_fields"] == ["name"]
    assert body["manager"] == {"enabled": True, "max_tasks": 6, "max_parallel": 2}
    assert body["agent_team"]["members"][0] == {
        "id": "scheduler", "stage_keys": ["book"], "tools": [],
    }
    assert body["call_stages"][0]["requirements"] == {
        "required_fields": ["name"], "successful_tools": [],
    }
    assert body["call_stages"][1]["specialist_id"] == "scheduler"
    assert body["call_stages"][1]["requirements"] == {"successful_tools": ["book_appointment"]}
    assert body["call_stages"][2] == {"key": "confirm", "tools": [], "next_stages": []}
    assert body["runtime_routing"] == {"enabled": False, "allowed_models": []}
    assert body["recording"] is False
    assert "voice_watcher" not in body and "telephony" not in body


def test_set_json_overrides_flags_and_preserves_reset(invoke):
    code, _, calls = invoke([
        "agents", "update", "desk", "--manager", "managed", "--set", "manager=false",
        "--s2s-provider", "openai", "--set", "realtime=null",
    ])
    assert code == cli.EXIT_OK
    assert calls[0][2] == {"manager": False, "realtime": None}


def test_planner_posts_inputs_without_creating_agent_or_forwarding_secrets(invoke, tmp_path):
    config = tmp_path / "plan.json"
    config.write_text(json.dumps({
        "manager": {"enabled": True},
        "supervisor": {"mode": "byok", "api_key": "secret-not-for-planner"},
        "callStages": [{"key": "confirm", "tools": [], "nextStages": []}],
    }))
    code, _, calls = invoke([
        "agents", "plan", "--description", "Book an approved slot", "--goal", "Book",
        "--direction", "inbound", "--stage-count", "3", "--config-file", str(config),
    ])
    assert code == cli.EXIT_OK
    assert calls == [("POST", "/api/v1/labs/agent-plans", {
        "description": "Book an approved slot", "goal": "Book", "direction": "inbound",
        "stage_count": 3, "call_stages": [{"key": "confirm", "tools": [], "next_stages": []}],
    })]


@pytest.mark.parametrize("argv,explanation", [
    (["agents", "update", "desk", "--s2s-model", "gpt-realtime-2.1"], "--s2s-provider"),
    (["agents", "update", "desk", "--s2s-provider", "ultravox", "--s2s-voice", "marin"], "--voice-provider"),
    (["agents", "update", "desk", "--supervisor", "managed", "--supervisor-model", "model"], "BYOK"),
    (["agents", "plan"], "requires"),
])
def test_invalid_combinations_never_reach_transport(invoke, argv, explanation):
    code, result, calls = invoke(argv)
    assert code == cli.EXIT_USAGE
    assert explanation in result["error"]["message"]
    assert calls == []


@pytest.mark.parametrize("count", ["2", "9"])
def test_stage_count_outside_supported_range_is_rejected_before_api(invoke, count):
    with pytest.raises(SystemExit) as error:
        invoke(["agents", "create", "--name", "Desk", "--stage-count", count])
    assert error.value.code == cli.EXIT_USAGE


def test_update_requires_an_explicit_plan_instead_of_stage_count(invoke):
    with pytest.raises(SystemExit) as error:
        invoke(["agents", "update", "desk", "--stage-count", "3"])
    assert error.value.code == cli.EXIT_USAGE


def test_runtime_read_can_select_provider_and_agency(invoke):
    code, _, calls = invoke(["--agency-id", "acct-1", "runtime", "get", "--provider", "hydra"])
    assert code == cli.EXIT_OK
    assert calls[0][0] == "GET"
    url = urlsplit(calls[0][1])
    assert url.path == "/api/v1/labs/runtime"
    assert parse_qs(url.query) == {"provider": ["smallest"], "agency_id": ["acct-1"]}


def test_runtime_read_without_provider_keeps_existing_request(invoke):
    code, _, calls = invoke(["runtime", "get"])
    assert code == cli.EXIT_OK
    assert calls == [("GET", "/api/v1/labs/runtime", None)]


def test_voice_filters_reach_wire(invoke):
    code, _, calls = invoke([
        "voices", "list", "--runtime-provider", "ultravox", "--provider", "cartesia",
        "--model", "sonic-3", "--configured-only",
    ])
    assert code == cli.EXIT_OK
    assert parse_qs(urlsplit(calls[0][1]).query) == {
        "provider": ["cartesia"], "runtime_provider": ["ultravox"], "model": ["sonic-3"],
        "configured_only": ["true"], "limit": ["50"],
    }


@pytest.mark.parametrize("env_name", ["OPENAI_API_KEY", "CUSTOM_SUPERVISOR_KEY"])
def test_byok_key_is_scrubbed_from_api_error(invoke, monkeypatch, capsys, env_name):
    secret = "private-supervisor-credential-123456"
    monkeypatch.setenv(env_name, secret)

    def transport(*_):
        raise SupafoneError(f"provider rejected {secret}", status=401)

    client = Supafone(api_key="sf_test_cli_factory", transport=transport)
    monkeypatch.setattr(cli, "build_client", lambda *_: client)
    code, result, _ = invoke([
        "agents", "update", "desk", "--supervisor", "openai", "--supervisor-api-key-env", env_name,
    ])
    assert code == cli.EXIT_API_ERROR
    assert secret not in json.dumps(result)
    assert "provider rejected" in result["error"]["message"]


def test_version_needs_no_credentials_or_api(monkeypatch, capsys):
    monkeypatch.delenv("SUPAFONE_API_KEY", raising=False)
    monkeypatch.setattr(cli, "build_client", lambda *_: pytest.fail("version must be local"))
    with pytest.raises(SystemExit) as error:
        cli.main(["--version"])
    assert error.value.code == cli.EXIT_OK
    assert capsys.readouterr().out.strip() == f"supafone {version('supafone-labs')}"


@pytest.mark.parametrize("alias,provider", [
    ("ultravox", "ultravox"), ("openai", "openai"), ("gemini", "google"),
    ("grok", "xai"), ("hydra", "smallest"),
])
def test_runtime_key_modes_and_env_input(invoke, monkeypatch, alias, provider):
    monkeypatch.setenv("FIXTURE_SPEAKING_KEY", "fixture-speaking-secret-1234")
    code, _, calls = invoke([
        "runtime", "update", "--provider", alias, "--mode", "byok",
        "--api-key-env", "FIXTURE_SPEAKING_KEY",
    ])
    assert code == cli.EXIT_OK
    assert calls[-1][2] == {
        "provider": provider, "mode": "byok", "credentials": {"api_key": "fixture-speaking-secret-1234"},
    }
    code, _, calls = invoke(["runtime", "update", "--provider", alias, "--mode", "supafone_managed"])
    assert code == cli.EXIT_OK
    assert calls[-1][2] == {"provider": provider, "mode": "supafone_managed"}


def test_runtime_env_key_only_keeps_ultravox_default(invoke, monkeypatch):
    monkeypatch.setenv("FIXTURE_SPEAKING_KEY", "fixture-speaking-secret-1234")
    code, _, calls = invoke(["runtime", "update", "--api-key-env", "FIXTURE_SPEAKING_KEY"])
    assert code == cli.EXIT_OK
    assert calls[-1][2] == {"provider": "ultravox", "credentials": {"api_key": "fixture-speaking-secret-1234"}}


def test_runtime_missing_env_and_managed_key_conflict_make_no_requests(invoke, monkeypatch):
    monkeypatch.delenv("MISSING_SPEAKING_KEY", raising=False)
    code, result, calls = invoke(["runtime", "update", "--provider", "openai", "--api-key-env", "MISSING_SPEAKING_KEY"])
    assert code == cli.EXIT_USAGE and calls == []
    assert "MISSING_SPEAKING_KEY" in result["error"]["message"]
    monkeypatch.setenv("FIXTURE_SPEAKING_KEY", "fixture-speaking-secret-1234")
    code, result, calls = invoke([
        "runtime", "update", "--provider", "openai", "--mode", "managed",
        "--api-key-env", "FIXTURE_SPEAKING_KEY",
    ])
    assert code == cli.EXIT_USAGE and calls == []
    assert "cannot include credentials" in result["error"]["message"]


@pytest.mark.parametrize("source", ["env", "credentials-file", "config-file", "set"])
@pytest.mark.parametrize("success", [True, False])
def test_runtime_credentials_scrubbed_everywhere(invoke, monkeypatch, tmp_path, source, success):
    secret = "fixture-speaking-secret-never-echo-12345"
    argv = ["runtime", "update", "--provider", "openai"]
    if source == "env":
        monkeypatch.setenv("FIXTURE_SPEAKING_KEY", secret)
        argv += ["--api-key-env", "FIXTURE_SPEAKING_KEY"]
    elif source == "set":
        argv += ["--set", "credentials=" + json.dumps({"api_key": secret})]
    else:
        path = tmp_path / "key.json"
        payload = {"api_key": secret} if source == "credentials-file" else {"credentials": {"api_key": secret}}
        path.write_text(json.dumps(payload))
        argv += [f"--{source}", str(path)]

    def transport(*_):
        if success:
            return {"message": f"Connected {secret}", "nested": {"provider_note": secret}}
        raise SupafoneError(f"Rejected {secret}", status=400, body={"detail": {"message": secret}})

    monkeypatch.setattr(cli, "build_client", lambda *_: Supafone(api_key="sf_test", transport=transport))
    code, result, _ = invoke(argv)
    assert code == (cli.EXIT_OK if success else cli.EXIT_API_ERROR)
    assert secret not in json.dumps(result)


def test_runtime_env_and_config_key_conflict_is_explicit(invoke, monkeypatch, tmp_path):
    monkeypatch.setenv("FIXTURE_SPEAKING_KEY", "fixture-speaking-secret-1234")
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"credentials": {"apiKey": "fixture-other-secret"}}))
    code, result, calls = invoke([
        "runtime", "update", "--provider", "openai", "--config-file", str(path),
        "--api-key-env", "FIXTURE_SPEAKING_KEY",
    ])
    assert code == cli.EXIT_USAGE and calls == []
    assert "not both" in result["error"]["message"]


def test_runtime_managed_reset_rejects_legacy_key_behind_empty_credentials(invoke, tmp_path):
    path = tmp_path / "runtime.json"
    path.write_text(json.dumps({
        "provider": "ultravox", "mode": "supafone_managed",
        "credentials": {"api_key": ""}, "ultravox": {"api_key": "fixture-legacy-secret"},
    }))
    code, result, calls = invoke(["runtime", "update", "--config-file", str(path)])
    assert code == cli.EXIT_USAGE and calls == []
    assert "cannot include credentials" in result["error"]["message"]
