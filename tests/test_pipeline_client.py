"""Hosted router contracts through real request normalization; no vendor calls."""
from copy import deepcopy
from itertools import product
import json
from pathlib import Path

import pytest

from supafone_labs import Supafone, SupafoneVoice, SupafoneS2S, SupafonePipeline, SupafoneRouter, UltravoxS2S, voice_catalog_snapshot
from supafone_labs.pipeline import normalize_pipeline

CONFIG = {
    "stt": {"provider": "cartesia", "model": "ink-2"},
    "llm": {"provider": "openai", "model": "gpt-4.1"},
    "tts": {"provider": "inworld", "model": "inworld-tts-2-flash", "voice": "Dennis"},
}

@pytest.fixture
def recorded():
    calls = []
    client = Supafone(api_key="sf_test", transport=lambda method, path, payload: calls.append((method,path,payload)) or {"success": True})
    return client, calls


def test_shared_superclass_preserves_ultravox_and_pipeline_factory(recorded):
    client, calls = recorded
    router = SupafoneRouter(client)
    hybrid = router.select({"kind": "hybrid"})
    assert isinstance(hybrid, UltravoxS2S)
    assert isinstance(hybrid, SupafoneS2S)
    assert isinstance(hybrid, SupafoneVoice)
    hybrid.create(name="Desk", voice={"provider": "cartesia", "voice_id": "existing-voice"})
    assert "realtime" not in calls[-1][2]
    assert "pipeline" not in calls[-1][2]
    engine = router.select({"kind": "pipeline", "pipeline": CONFIG})
    assert isinstance(engine, SupafoneVoice)
    engine.create(name="Desk", supervisor=True, manager={"enabled":True,"reasoning":"managed"})
    assert calls[-1][2]["pipeline"] == normalize_pipeline(CONFIG)
    assert calls[-1][2]["voice_watcher"] is True
    assert calls[-1][2]["manager"]["enabled"] is True


def test_apply_clears_route_without_resetting_workflow(recorded):
    client, calls = recorded
    SupafonePipeline(client, **CONFIG).apply("desk/one", agency_id="account 1")
    assert calls[-1] == ("PATCH", "/api/v1/labs/agents/desk%2Fone?agency_id=account+1", {"pipeline": normalize_pipeline(CONFIG), "realtime": None})
    UltravoxS2S(client).apply("desk/one")
    assert calls[-1][2] == {"realtime": None}  # backend clears pipeline for legacy clients
    client.labs.agents.update("desk", pipeline=None)
    assert calls[-1][2] == {"pipeline": None}


def test_preview_is_never_an_implicit_switch(recorded):
    client, calls = recorded
    SupafonePipeline(client, **CONFIG).test_call("desk/one")
    assert calls == [("POST", "/api/v1/labs/agents/desk%2Fone/test-call", None)]


@pytest.mark.parametrize("modes", product(("managed", "byok"), repeat=3))
def test_every_credential_vector_preserves_independent_modes(recorded, modes):
    client, calls = recorded
    credentials = dict(zip(("stt", "llm", "tts"), modes))
    SupafonePipeline(client, **CONFIG, credentials=credentials).apply("desk")
    assert calls[-1][2]["pipeline"]["credentials"] == {"default":"auto", **credentials}


@pytest.mark.parametrize("change", [
    {"schema_version":2}, {"schema_version":True}, {"stt":None},
    {"llm":{"provider":"openai","model":" "}},
    {"tts":{"provider":"inworld","model":"model","api_key":"secret-value"}},
    {"stt":{"provider":"cartesia","model":"ink-2","options":{"authorization":"secret"}}},
    {"stt":{"provider":"cartesia","model":"ink-2","voice":"bad"}},
    {"llm":{"provider":"openai","model":"gpt-4.1","options":{"temperature":float('nan')}}},
    {"credentials":{"default":"fallback"}}, {"transport":"unknown"},
])
def test_invalid_or_secret_config_fails_before_network(recorded, change):
    client, calls = recorded
    with pytest.raises((ValueError, TypeError)):
        SupafonePipeline(client, **{**CONFIG, **change})
    assert not calls


def test_conflicting_direct_agent_routes_fail_before_network(recorded):
    client, calls = recorded
    with pytest.raises(ValueError, match="mutually exclusive"):
        client.labs.agents.create(name="Desk", pipeline=CONFIG, realtime={"provider":"openai"})
    with pytest.raises(ValueError, match="adapter"):
        SupafoneS2S(client).create(name="Desk", pipeline=CONFIG)
    assert not calls


def test_selection_is_a_deep_copy(recorded):
    client, _ = recorded
    config = deepcopy(CONFIG)
    engine = SupafonePipeline(client, **config)
    config["stt"]["model"] = "changed"
    engine.pipeline["tts"]["voice"] = "changed"
    assert engine.pipeline["stt"]["model"] == "ink-2"
    assert engine.pipeline["tts"]["voice"] == "Dennis"


def test_catalog_validation_enumeration_and_profile_contracts(recorded):
    client, calls = recorded
    voice = client.labs.voice
    voice.catalog(layer="stt")
    assert calls[-1] == ("GET", "/api/v1/labs/voice/catalog?layer=stt", None)
    voice.combinations(filters={"stt":["stt/cartesia/ink-2"]},context={"language":"en"}, offset=100, limit=50)
    assert calls[-1][2] == {"filters":{"stt":["stt/cartesia/ink-2"]},"context":{"language":"en"},"offset":100,"limit":50}
    SupafonePipeline(client, **CONFIG).validate(context={"transport":"browser"})
    assert calls[-1][2] == {"pipeline":normalize_pipeline(CONFIG),"realtime":None,"context":{"transport":"browser"}}
    voice.configure_profile("google", "stt", profile="work", mode="byok", credentials={"project_id":"project","service_account_json":json.dumps({"type":"service_account","private_key":"test-only-secret","project_id":"project","client_email":"service@test.example","token_uri":"https://oauth2.googleapis.com/token"})})
    assert calls[-1][1] == "/api/v1/labs/voice/profiles/google/stt/work"
    voice.get_profile("google", "stt", profile="work")
    assert calls[-1][0] == "GET"
    voice.configure_profile("google", "stt", profile="work", mode="managed")
    assert calls[-1][2] == {"mode":"managed","credentials":{}}
    before = len(calls)
    with pytest.raises(ValueError):
        voice.configure_profile("google", "stt", mode="managed", credentials={"api_key":"no"})
    assert len(calls) == before


def test_every_catalog_triple_can_be_selected_without_a_curated_allowlist(recorded):
    client, calls = recorded
    catalog = voice_catalog_snapshot()
    layers = [[entry for entry in catalog["components"] if entry["layer"] == layer] for layer in ("stt", "llm", "tts")]
    assert all(layers)
    count = 0
    for triple in product(*layers):
        config = {layer:{"provider":entry["provider"],"model":entry["model"]} for layer,entry in zip(("stt","llm","tts"), triple)}
        SupafonePipeline(client, **config).apply("desk")
        assert {layer:calls[-1][2]["pipeline"][layer] for layer in ("stt","llm","tts")} == config
        count += 1
        calls.clear()
    assert count == len(layers[0]) * len(layers[1]) * len(layers[2])


def test_python_and_typescript_share_the_same_generated_manifest():
    root = Path(__file__).resolve().parents[1]
    source = (root / "sdk-ts/src/voice-catalog.ts").read_text()
    embedded = source.split("const snapshot = ", 1)[1].split(";\nexport function", 1)[0]
    assert json.loads(embedded) == voice_catalog_snapshot()


def test_legacy_empty_realtime_reset_is_still_transmitted(recorded):
    client, calls = recorded
    client.labs.agents.update("desk", realtime={})
    assert calls[-1][2] == {"realtime": {}}


def test_workspace_preflight_and_profiles_use_the_explicit_account(recorded):
    client, calls = recorded
    SupafonePipeline(client, **CONFIG).validate(agency_id="other-account")
    assert calls[-1][2]["agency_id"] == "other-account"
    SupafoneRouter(client).validate({"kind":"hybrid"}, agency_id="other-account")
    assert calls[-1][2] == {"realtime":None,"agency_id":"other-account"}
    client.labs.voice.get_profile("openai","llm",agency_id="other-account",mode="managed")
    assert calls[-1][1].endswith("?mode=managed&agency_id=other-account")
