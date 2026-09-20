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
