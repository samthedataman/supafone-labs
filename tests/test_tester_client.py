"""Provider-neutral real phone tester in the Python SDK."""

import pytest

from supafone_labs import Supafone


def _client(calls, response=None):
    supafone = Supafone(api_key="sl_test")

    def fake_labs_api(method, path, payload=None, *, use_session=False):
        calls.append((method, path, payload, use_session))
        return dict(response or {})

    supafone._request_labs_api = fake_labs_api
    return supafone


def test_tester_grade_agent_preserves_target_provider_metadata():
    calls = []
    supafone = _client(calls, {"session_id": "ts_123", "status": "dialing"})

    result = supafone.tester.grade_agent(
        to_number="+14155550100",
        scenario="language_switch",
        agent_label="grok-agent",
        ai_provider="grok",
        telephony_provider="telnyx",
        authorized=True,
    )

    assert result["session_id"] == "ts_123"
    method, path, payload, use_session = calls[0]
    assert (method, path, use_session) == ("POST", "/v1/tester/call", False)
    assert payload == {
        "to_number": "+14155550100",
        "scenario": "language_switch",
        "agent_label": "grok-agent",
        "ai_provider": "grok",
        "telephony_provider": "telnyx",
        "authorized": True,
    }


@pytest.mark.parametrize("authorized,number", [(False, "+14155550100"), (True, "415-555-0100")])
def test_tester_grade_agent_requires_permission_and_e164(authorized, number):
    supafone = _client([])
    with pytest.raises(ValueError):
        supafone.tester.grade_agent(to_number=number, authorized=authorized)


def test_tester_wait_returns_terminal_session_without_vendor_assumptions():
    supafone = _client([])
    sessions = iter([
        {"status": "dialing", "transcript": []},
        {
            "status": "done",
            "transcript": [{"role": "agent", "text": "Hello"}],
            "verdict": {"passed": True, "score": 0.92},
            "target": {"ai_provider": "gpt_realtime", "telephony_provider": "twilio"},
        },
    ])
    supafone.tester.session = lambda _session_id: next(sessions)

    result = supafone.tester.wait("ts_123", poll_seconds=0.001, timeout_seconds=1)

    assert result["status"] == "done"
    assert result["target"]["ai_provider"] == "gpt_realtime"
