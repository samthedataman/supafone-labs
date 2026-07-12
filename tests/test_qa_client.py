"""The Python client's QA + post-call-analysis surface (parity with the TS SDK)."""

from supafone_labs import Supafone


def _client_with_labs_recorder(calls, response=None, **kwargs):
    supafone = Supafone(api_key="sl_test", **kwargs)

    def fake_labs_api(method, path, payload=None, *, use_session=False):
        calls.append((method, path, payload, use_session))
        return dict(response or {})

    supafone._request_labs_api = fake_labs_api
    return supafone


def test_qa_generate_is_key_scoped():
    calls = []
    supafone = _client_with_labs_recorder(calls, {"scenarios": [{"title": "Refund bully"}]})
    out = supafone.qa.generate("You are an intake agent.", count=3)
    assert out["scenarios"][0]["title"] == "Refund bully"
    method, path, payload, use_session = calls[0]
    assert (method, path) == ("POST", "/v1/qa/generate")
    assert payload == {"agent_prompt": "You are an intake agent.", "count": 3}
    assert use_session is False


def test_qa_suite_and_run_are_session_scoped():
    calls = []
    supafone = _client_with_labs_recorder(calls, {"summary": {}})
    supafone.qa.suite(count=4, turns=2, supervised=True)
    supafone.qa.run(scenarios=["refund_bully"], turns=3)
    assert calls[0][:3] == ("POST", "/v1/qa/suite", {"count": 4, "turns": 2, "supervised": True})
    assert calls[0][3] is True
    assert calls[1][:3] == ("POST", "/v1/qa/run", {"scenarios": ["refund_bully"], "turns": 3})
    assert calls[1][3] is True


def test_qa_history_uses_key():
    calls = []
    supafone = _client_with_labs_recorder(calls, {"runs": []})
    supafone.qa.history(agent="intake", limit=10)
    method, path, payload, use_session = calls[0]
    assert method == "GET" and "agent=intake" in path and "limit=10" in path
    assert use_session is False


def test_report_call_plain_without_flag():
    calls = []
    supafone = _client_with_labs_recorder(calls, {"recorded": True})
    out = supafone.report_call({"session_id": "s1", "score": 0.9, "transcript": "caller: hi"})
    # Without post_call_analysis the transcript is stripped and the plain report files.
    assert out["recorded"] is True and "analysis" not in out
    method, path, payload, _ = calls[0]
    assert (method, path) == ("POST", "/v1/events/call_report")
    assert "transcript" not in payload


def test_report_call_auto_classifies_with_flag():
    calls = []
    supafone = _client_with_labs_recorder(
        calls,
        {"achieved": True, "criteria": {"intent_satisfied": True}, "failure_reasons": []},
        post_call_analysis=True,
    )
    out = supafone.report_call(
        {
            "session_id": "s1",
            "agent": "intake",
            "transcript": "caller: I want to book\nagent: Booked for 3pm",
            "ground_truth": {"booking_requested": True, "booking_verified": True},
        }
    )
    assert out["recorded"] is True
    assert out["analysis"]["achieved"] is True
    method, path, payload, _ = calls[0]
    assert (method, path) == ("POST", "/v1/calls/classify")
    assert payload["agent"] == "intake"
    assert payload["ground_truth"]["booking_verified"] is True
    # classify files the enriched report server-side — exactly one request, no double-file.
    assert len(calls) == 1
