"""Speaking key configuration uses one account contract across all providers."""
from urllib.parse import parse_qs, urlsplit

import pytest

from supafone_labs import Supafone


PROVIDERS = ("ultravox", "openai", "google", "xai", "smallest")


@pytest.fixture
def recording_client():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"provider": "openai", "configured": False, "connected": True, "source": "platform"}

    return Supafone(api_key="sf_test_runtime", transport=transport), calls


@pytest.mark.parametrize("provider", PROVIDERS)
def test_readiness_and_both_key_modes(recording_client, provider):
    client, calls = recording_client
    result = client.labs.runtime.get(provider=provider, agency_id="account/one")
    assert result["source"] == "platform"
    assert parse_qs(urlsplit(calls[-1][1]).query) == {
        "provider": [provider], "agency_id": ["account/one"],
    }
    client.labs.runtime.configure(provider=provider, mode="byok", credentials={"api_key": "fixture-key"})
    assert calls[-1] == ("PUT", "/api/v1/labs/runtime", {
        "provider": provider, "mode": "byok", "credentials": {"api_key": "fixture-key"},
    })
    client.labs.runtime.configure(provider=provider, mode="supafone_managed")
    assert calls[-1] == ("PUT", "/api/v1/labs/runtime", {
        "provider": provider, "mode": "supafone_managed",
    })


def test_legacy_no_mode_payload_is_preserved(recording_client):
    client, calls = recording_client
    client.labs.runtime.configure(agencyId="account", ultravox={"api_key": "fixture-key"})
    assert calls[-1][2] == {
        "agency_id": "account", "provider": "ultravox", "credentials": {"api_key": "fixture-key"},
    }
    client.labs.runtime.configure(provider="openai", mode="managed")
    assert calls[-1][2] == {"provider": "openai", "mode": "supafone_managed"}


@pytest.mark.parametrize("credentials", [{"api_key": "fixture-key"}, {"apiKey": "fixture-key"}, {"base_url": "https://example.test"}])
def test_managed_mode_rejects_credentials_without_a_request(recording_client, credentials):
    client, calls = recording_client
    with pytest.raises(ValueError, match="cannot include credentials"):
        client.labs.runtime.configure(provider="openai", mode="supafone_managed", credentials=credentials)
    assert calls == []


def test_unknown_mode_is_not_silently_dropped(recording_client):
    client, calls = recording_client
    with pytest.raises(ValueError, match="runtime mode"):
        client.labs.runtime.configure(provider="openai", mode="something-else")
    assert calls == []


@pytest.mark.parametrize("credentials,legacy", [
    ({"api_key": ""}, {"api_key": "fixture-legacy-secret"}),
    ({"api_key": "fixture-current-secret"}, {"api_key": ""}),
    ({}, "not-an-object"),
    ("not-an-object", {}),
])
def test_managed_reset_validates_both_credential_aliases(recording_client, credentials, legacy):
    client, calls = recording_client
    with pytest.raises(ValueError, match="credentials"):
        client.labs.runtime.configure(
            mode="supafone_managed", credentials=credentials, ultravox=legacy,
        )
    assert calls == []
