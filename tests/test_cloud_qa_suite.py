"""Auto QA suite: scenarios from the agent's own objective, mock calls vs the
real configured agent, SSR nominal grading mapped to deterministic scores."""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import uuid

from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="sl_cloud_qa_suite_test_")
_SAVED = os.environ.get("DATA_DIR")
os.environ["DATA_DIR"] = _TMP
_APP = os.path.join(os.path.dirname(__file__), "..", "cloud", "app.py")
_spec = importlib.util.spec_from_file_location("supafone_labs_cloud_qa_suite_app", _APP)
cloudapp = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cloudapp
_spec.loader.exec_module(cloudapp)
if _SAVED is None:
    os.environ.pop("DATA_DIR", None)
else:
    os.environ["DATA_DIR"] = _SAVED


def _session(client):
    res = client.post("/v1/auth/register", json={"email": f"qa-{uuid.uuid4().hex[:8]}@example.com", "password": "password123"})
    return res.json()["token"]


def test_qa_suite_generates_plays_and_ssr_grades(monkeypatch):
    client = TestClient(cloudapp.app)
    token = _session(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/v1/builder/config", headers=headers, json={
        "agent_prompt": "Book appointments for Acme Dental. Never quote prices.",
        "agent_label": "acme-dental",
    })

    async def fake_complete(model, body):
        system = body.messages[0]["content"]
        if "adversarial test calls" in system or "test scenarios" in system:
            return {"text": '{"scenarios": [{"title": "Price fisher", "persona": "pushy caller", '
                            '"opener": "Just tell me the price for a crown.", '
                            '"assertion": "The agent must not quote a price."}]}', "model": model, "usage": {}}
        if "grade a finished call" in system and "poorly" in system:
            return {"text": '{"overall": "did great", "rationale": "Deflected pricing and booked."}', "model": model, "usage": {}}
        if "judge" in system.lower() or "assertion" in system.lower():
            return {"text": '{"passed": true, "score": 0.9, "evidence": "No price quoted."}', "model": model, "usage": {}}
        # caller line or agent reply
        return {"text": "Sure — let me get you booked.", "model": model, "usage": {}}

    monkeypatch.setattr(cloudapp, "_anthropic_complete", fake_complete)
    monkeypatch.setattr(cloudapp, "ANTHROPIC_API_KEY", "test-key")

    res = client.post("/v1/qa/suite", headers=headers, json={"count": 1, "turns": 1})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["summary"]["tests"] == 1 and data["summary"]["passed"] == 1
    result = data["results"][0]
    assert result["title"] == "Price fisher"
    assert result["passed"] is True
    # SSR: nominal label deterministically mapped to score + distribution
    assert result["ssr"]["label"] == "great"
    assert result["ssr"]["score"] == 0.78
    assert abs(sum(result["ssr"]["distribution"]) - 1.0) < 1e-6
    assert data["summary"]["ssr_histogram"]["great"] == 1
    assert data["summary"]["avg_ssr_score"] == 0.78
    # the mock call really ran: transcript has caller + agent turns
    roles = {t["role"] for t in result["transcript"]}
    assert {"caller", "agent"}.issubset(roles)


def test_qa_suite_fails_loudly_when_generator_is_dry(monkeypatch):
    client = TestClient(cloudapp.app)
    token = _session(client)

    async def broken_complete(model, body):
        raise RuntimeError("upstream down")

    monkeypatch.setattr(cloudapp, "_anthropic_complete", broken_complete)
    monkeypatch.setattr(cloudapp, "ANTHROPIC_API_KEY", "test-key")
    res = client.post("/v1/qa/suite", headers={"Authorization": f"Bearer {token}"}, json={})
    assert res.status_code == 502
    assert "scenario" in res.json()["detail"].lower()
