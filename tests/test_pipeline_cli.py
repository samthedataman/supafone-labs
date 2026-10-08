"""Real CLI -> SDK -> recording transport tests, with no paid sessions."""
import json
import pytest
from supafone_labs import Supafone, cli
CONFIG = {
    "stt": {"provider": "cartesia", "model": "ink-2"},
    "llm": {"provider": "openai", "model": "gpt-4.1"},
    "tts": {"provider": "inworld", "model": "inworld-tts-2-flash", "voice": "Dennis"},
}

@pytest.fixture
def invoke(monkeypatch, capsys):
    monkeypatch.setenv("SUPAFONE_API_KEY", "sf_test")
    calls = []
    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success":True}
    monkeypatch.setattr(cli, "build_client", lambda *_: Supafone(api_key="sf_test", transport=transport))
    def run(args):
        status = cli.main(args)
        output = capsys.readouterr()
        return status, json.loads(output.out if status == 0 else output.err), calls
    return run


def test_pipeline_agent_create_validate_apply_and_preview(invoke, tmp_path):
    path = tmp_path / "pipeline.json"
    path.write_text(json.dumps(CONFIG))
    code, _, calls = invoke(["agents","create","--name","Desk","--pipeline-file",str(path),"--supervisor","managed","--manager","managed"])
    assert code == 0
    assert calls[-1][2]["pipeline"]["stt"] == CONFIG["stt"]
    assert calls[-1][2]["manager"]["enabled"]
    code, _, calls = invoke(["pipeline","validate","--config-file",str(path),"--json"])
    assert code == 0
    assert calls[-1][1] == "/api/v1/labs/voice/validate"
    code, _, calls = invoke(["pipeline","apply","desk","--config-file",str(path)])
    assert code == 0
    assert calls[-1][2]["realtime"] is None
    code, _, calls = invoke(["pipeline","test-call","desk"])
    assert code == 0
    assert calls[-1] == ("POST","/api/v1/labs/agents/desk/test-call",None)


def test_conflicting_native_and_pipeline_selection_rejected(invoke, tmp_path):
    path = tmp_path / "pipeline.json"
    path.write_text(json.dumps(CONFIG))
    code, _, calls = invoke(["agents","create","--name","Desk","--pipeline-file",str(path),"--s2s-provider","openai"])
    assert code == cli.EXIT_USAGE
    assert not calls


def test_profile_byok_modes_are_independent_and_secrets_are_redacted(invoke, monkeypatch):
    monkeypatch.setenv("MY_VOICE_KEY", "provider-test-secret")
    code, _, calls = invoke(["router","profile","set","--provider","inworld","--service","tts","--mode","byok","--api-key-env","MY_VOICE_KEY"])
    assert code == 0
    assert calls[-1][2] == {"mode":"byok","credentials":{"api_key":"provider-test-secret"}}
    monkeypatch.setenv("MY_CLOUD_PROFILE", json.dumps({"project_id":"test", "service_account_json":json.dumps({"type":"service_account","project_id":"test","client_email":"service@test.example","private_key":"profile-test-secret","token_uri":"https://oauth2.googleapis.com/token"})}))
    code, _, calls = invoke(["pipeline","profile","set","--provider","google","--service","stt","--mode","byok","--credentials-env","MY_CLOUD_PROFILE"])
    assert code == 0
    assert json.loads(calls[-1][2]["credentials"]["service_account_json"])["private_key"] == "profile-test-secret"
    before = len(calls)
    code, _, calls = invoke(["router","profile","set","--provider","openai","--service","llm","--mode","managed","--api-key-env","MY_VOICE_KEY"])
    assert code == cli.EXIT_USAGE
    assert len(calls) == before


def test_full_pagination_never_silently_drops_tuples(monkeypatch, capsys):
    monkeypatch.setenv("SUPAFONE_API_KEY", "sf_test")
    pages = []
    def transport(method,path,payload):
        pages.append(payload)
        offset = payload["offset"]
        return {"registry_hash":"same", "counts":{"raw_triples":3}, "combinations":[{"id":str(offset)}], "next_offset":offset+1 if offset < 2 else None}
    monkeypatch.setattr(cli,"build_client",lambda *_:Supafone(api_key="sf_test",transport=transport))
    assert cli.main(["router","combinations","--all","--explain","--limit","1","--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert len(result["data"]["combinations"]) == 3
    assert [p["offset"] for p in pages] == [0,1,2]


@pytest.mark.parametrize("profile,secrets", [
    ({"region":"us-east-1","access_key_id":"AKIA-TEST-CLOUD-KEY","secret_access_key":"aws-test-secret-access-value"}, ["AKIA-TEST-CLOUD-KEY","aws-test-secret-access-value"]),
    ({"project_id":"test","service_account_json":json.dumps({"type":"service_account","project_id":"test","client_email":"service@test.example","private_key":"long-private-secret", "token_uri":"https://oauth2.googleapis.com/token"})}, ["long-private-secret"]),
])
def test_profile_values_scrubbed_even_from_upstream_error(monkeypatch, capsys, profile, secrets):
    from supafone_labs.client import SupafoneError
    monkeypatch.setenv("SUPAFONE_API_KEY","sf_test")
    monkeypatch.setenv("CLOUD_JSON", json.dumps(profile))
    def transport(*args):
        raise SupafoneError("Rejected " + " / ".join(secrets))
    monkeypatch.setattr(cli,"build_client",lambda *_:Supafone(api_key="sf_test",transport=transport))
    cli.main(["router","profile","set","--provider","google","--service","stt","--mode","byok","--credentials-env","CLOUD_JSON"])
    error = capsys.readouterr().err
    assert all(secret not in error for secret in secrets)
    assert all(secret not in json.dumps(cli.redact(profile)) for secret in secrets)
