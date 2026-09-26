from supafone_labs import Supafone


def test_realtime_factory_payload_preserves_selection_and_server_stages():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {"agent_key": "phone-demo"}, "runtime": {}}

    client = Supafone(api_key="sf_test", transport=transport)
    client.labs.agents.create_outbound(
        name="Phone demo",
        realtime={
            "provider": "google",
            "model": "gemini-3.1-flash-live-preview",
            "voice": "Puck",
        },
        telephony={"mode": "byok", "provider": "telnyx"},
    )

    method, path, payload = calls[0]
    assert (method, path) == ("POST", "/api/v1/labs/agents")
    assert payload["realtime"] == {
        "provider": "google",
        "model": "gemini-3.1-flash-live-preview",
        "voice": "Puck",
    }
    assert "call_stages" not in payload


def test_realtime_test_call_uses_authenticated_agent_route():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"simulated": True}

    client = Supafone(api_key="sf_test", transport=transport)
    result = client.labs.agents.test_call("demo/one", agency_id="acct-1")

    assert result == {"simulated": True}
    assert calls == [
        ("POST", "/api/v1/labs/agents/demo%2Fone/test-call?agency_id=acct-1", None)
    ]


def test_realtime_switch_and_reset_preserve_explicit_selection():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True}

    client = Supafone(api_key="sf_test", transport=transport)
    selection = {"provider": "xai", "model": "grok-voice-latest", "voice": "eve"}
    client.labs.agents.update("demo", realtime=selection)
    client.labs.agents.update("demo", realtime=None)
    client.labs.agents.update("demo", name="Renamed")
    assert calls[0] == ("PATCH", "/api/v1/labs/agents/demo", {"realtime": selection})
    assert calls[1] == ("PATCH", "/api/v1/labs/agents/demo", {"realtime": None})
    assert "realtime" not in calls[2][2]
