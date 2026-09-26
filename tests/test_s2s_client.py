"""Consumer contract for the shared provider interface and real request payloads."""

import pytest

from supafone_labs import (
    GeminiS2S,
    GrokS2S,
    HydraS2S,
    OpenAIS2S,
    Supafone,
    SupafoneS2S,
    UltravoxS2S,
)


@pytest.fixture
def client_and_calls():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {"agent_key": "same-agent"}}

    return Supafone(api_key="sf_test", transport=transport), calls


@pytest.mark.parametrize(
    "adapter,provider",
    [
        (UltravoxS2S, "ultravox"),
        (OpenAIS2S, "openai"),
        (GeminiS2S, "google"),
        (GrokS2S, "xai"),
        (HydraS2S, "smallest"),
    ],
)
def test_all_providers_share_the_factory_and_preserve_configuration(
    client_and_calls, adapter, provider
):
    client, calls = client_and_calls
    engine = adapter(client)
    assert isinstance(engine, SupafoneS2S)
    result = engine.create(
        name="Concierge",
        goal="Book a consultation",
        description="Welcome callers and collect intake details",
        telephony={
            "mode": "byok",
            "provider": "telnyx",
        },
    )
    method, path, payload = calls[0]
    assert (method, path) == ("POST", "/api/v1/labs/agents")
    assert result["agent"]["agent_key"] == "same-agent"
    assert payload["goal"] == "Book a consultation"
    assert payload["description"] == "Welcome callers and collect intake details"
    assert payload["telephony"]["provider"] == "telnyx"
    assert engine.provider == provider
    if provider == "ultravox":
        assert "realtime" not in payload
    else:
        assert payload["realtime"] == {"provider": provider}
        assert "call_stages" not in payload


def test_switch_and_reset_only_patch_same_agent_selection(client_and_calls):
    client, calls = client_and_calls
    engine = HydraS2S(client, model="hydra-v1.1", voice="maya")
    engine.apply("demo/one", agency_id="account 1")
    UltravoxS2S(client).apply("demo/one", agency_id="account 1")
    assert calls == [
        (
            "PATCH",
            "/api/v1/labs/agents/demo%2Fone?agency_id=account+1",
            {
                "realtime": {
                    "provider": "smallest",
                    "model": "hydra-v1.1",
                    "voice": "maya",
                }
            },
        ),
        ("PATCH", "/api/v1/labs/agents/demo%2Fone?agency_id=account+1", {"realtime": None}),
    ]


def test_preview_does_not_implicitly_change_saved_provider(client_and_calls):
    client, calls = client_and_calls
    HydraS2S(client).test_call("demo/one", agency_id="account-1")
    assert calls == [
        ("POST", "/api/v1/labs/agents/demo%2Fone/test-call?agency_id=account-1", None),
    ]


def test_smallest_optional_account_key_alias_is_preserved(client_and_calls):
    client, calls = client_and_calls
    HydraS2S(client).create(name="Demo", provider_keys={"smallestApiKey": "test-key"})
    assert calls[0][2]["provider_keys"] == {"smallest_api_key": "test-key"}


def test_adapter_rejects_conflicting_selection_and_unknown_provider(client_and_calls):
    client, calls = client_and_calls
    with pytest.raises(ValueError, match="Unsupported"):
        SupafoneS2S(client, provider="unknown")
    with pytest.raises(ValueError, match="voice settings"):
        SupafoneS2S(client, model="gpt-live-1")
    with pytest.raises(ValueError, match="non-empty"):
        HydraS2S(client, voice=" ")
    with pytest.raises(ValueError, match="S2S adapter"):
        HydraS2S(client).create(name="Conflict", realtime={"provider": "xai"})
    with pytest.raises(ValueError, match="agent_key"):
        HydraS2S(client).apply("")
    assert calls == []


def test_exported_selection_is_not_mutable_adapter_state(client_and_calls):
    client, _ = client_and_calls
    engine = HydraS2S(client, model="hydra-v1.0", voice="sterling")
    selection = engine.realtime
    selection["provider"] = "xai"
    assert engine.realtime["provider"] == "smallest"
