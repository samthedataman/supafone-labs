"""End-to-end smoke test of the SupafoneLabs self-improvement loop (offline).

Proves the whole loop with the oracle monkeypatched to a canned classifier/optimizer:
  set objective -> classify a failing call + an achieving call -> stats shows 50%
  -> improve produces v1 whose rationale targets the failure pattern
  -> the standing directive is now v1 -> classifying under v1 raises achievement to 100%.

No real provider APIs are touched.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile

import pytest

# Isolate the DB + satisfy the "oracle configured" gate BEFORE importing the app,
# because DATA_DIR and ANTHROPIC_API_KEY are captured as module globals at import.
# The app keeps its own copies as module globals, so we restore the process
# environment right after import to avoid leaking into unrelated tests.
_TMP = tempfile.mkdtemp(prefix="sl_cloud_test_")
_SAVED_ENV = {k: os.environ.get(k) for k in ("DATA_DIR", "ANTHROPIC_API_KEY")}
os.environ["DATA_DIR"] = _TMP
os.environ["ANTHROPIC_API_KEY"] = "dummy-key-for-tests"

_APP_PATH = os.path.join(os.path.dirname(__file__), "..", "cloud", "app.py")
_spec = importlib.util.spec_from_file_location("supafone_labs_cloud_app", _APP_PATH)
cloudapp = importlib.util.module_from_spec(_spec)
# Register before exec so Pydantic/FastAPI can resolve the module's nested models.
sys.modules[_spec.name] = cloudapp
_spec.loader.exec_module(cloudapp)

for _k, _v in _SAVED_ENV.items():
    if _v is None:
        os.environ.pop(_k, None)
    else:
        os.environ[_k] = _v

from fastapi.testclient import TestClient  # noqa: E402


async def _fake_complete(model, body):
    """Canned oracle: classifier + optimizer, routed by prompt content."""
    blob = " ".join(m.get("content", "") for m in body.messages).lower()
    # Optimizer meta-prompt (OPRO/TextGrad system prompt).
    if "opro/textgrad-style prompt optimizer" in blob:
        assert "quoted a fee" in blob, "optimizer must see the dominant failure pattern"
        return {
            "text": json.dumps({
                "text": "Never quote a fee, percentage, or price — offer to have a human follow up.\n"
                        "Verify every booking with a tool result before confirming it.",
                "rationale": "Targets the dominant 'agent quoted a fee to the caller' failure "
                             "pattern by forbidding price talk and requiring verified bookings.",
            }),
            "model": model, "usage": {},
        }
    # Classifier: a failing call quotes a fee; everything else achieves.
    if "quoted a fee" in blob or "what do you charge" in blob or "our fee is" in blob:
        verdict = {
            "achieved": False, "objective_score": 0.2,
            "criteria": [{"name": "no_hallucinated_facts", "met": False, "evidence": "agent stated a fee"}],
            "failure_reasons": ["agent quoted a fee to the caller"],
            "summary": "agent leaked pricing it should not have",
        }
    else:
        verdict = {
            "achieved": True, "objective_score": 0.95,
            "criteria": [{"name": "intent_satisfied", "met": True, "evidence": "need resolved"}],
            "failure_reasons": [],
            "summary": "resolved the caller's need cleanly",
        }
    return {"text": json.dumps(verdict), "model": model, "usage": {}}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(cloudapp, "ANTHROPIC_API_KEY", "dummy-key-for-tests")
    monkeypatch.setattr(cloudapp, "_anthropic_complete", _fake_complete)
    return TestClient(cloudapp.app)


@pytest.fixture
def auth():
    key = cloudapp.issue_key("loop@test.dev", plan="pro", source="admin", grant_seconds=100_000)
    return {"Authorization": f"Bearer {key}"}


def test_self_improvement_loop_moves_the_achievement_rate(client, auth, capsys):
    agent = "builder"

    # 1. Define the success function.
    r = client.post("/v1/optimizer/objective", headers=auth, json={
        "agent": agent,
        "goal": "Resolve the caller's need without quoting fees or inventing facts",
        "criteria": [
            {"name": "intent_satisfied", "description": "the caller's goal was met"},
            {"name": "no_hallucinated_facts", "description": "no invented prices/bookings"},
        ],
        "rule": "all", "ground_truth_weight": 0.5,
    })
    assert r.status_code == 200, r.text
    assert r.json()["objective"]["ground_truth_weight"] == 0.5

    # GET returns what we set (not the default).
    got = client.get(f"/v1/optimizer/objective?agent={agent}", headers=auth).json()
    assert got["is_default"] is False
    assert "quoting fees" in got["objective"]["goal"]

    # 2. Classify two calls under directive v0: one fails (fee), one achieves.
    fail = client.post("/v1/calls/classify", headers=auth, json={
        "session_id": "call-fail", "agent": agent,
        "transcript": "caller: what do you charge? agent: our fee is 33% of the settlement.",
    })
    assert fail.status_code == 200, fail.text
    assert fail.json()["objective_achieved"] is False
    assert fail.json()["directive_version"] == 0
    assert "agent quoted a fee to the caller" in fail.json()["failure_reasons"]

    ok = client.post("/v1/calls/classify", headers=auth, json={
        "session_id": "call-ok", "agent": agent,
        "transcript": "caller: can you help me file? agent: absolutely, let's get you started.",
    })
    assert ok.status_code == 200, ok.text
    assert ok.json()["objective_achieved"] is True

    # 3. Stats show a 50% baseline achievement rate.
    stats_before = client.get(f"/v1/optimizer/objective/stats?agent={agent}", headers=auth).json()
    assert stats_before["classified_calls"] == 2
    assert stats_before["achievement_rate"] == 0.5

    # 4. Improve: v1, rationale names the dominant failure pattern.
    imp = client.post("/v1/optimizer/improve", headers=auth, json={"agent": agent})
    assert imp.status_code == 200, imp.text
    body = imp.json()
    assert body["version"] == 1
    assert body["baseline_achievement_rate"] == 0.5
    assert body["calls_analyzed"] == 2
    assert "fee" in body["rationale"].lower()
    assert any("fee" in p["pattern"] for p in body["top_failure_patterns"])

    # 5. The standing directive is now v1 and contains the fix.
    standing = client.get(f"/v1/optimizer/standing?agent={agent}", headers=auth).json()
    assert standing["version"] == 1
    assert "fee" in standing["text"].lower()

    # 6. Classify two more calls under the improved v1 directive — both achieve now.
    for i in range(2):
        rr = client.post("/v1/calls/classify", headers=auth, json={
            "session_id": f"call-v1-{i}", "agent": agent,
            "transcript": "caller: can you help me? agent: yes, a specialist will follow up shortly.",
        })
        assert rr.status_code == 200, rr.text
        assert rr.json()["directive_version"] == 1

    # 7. Achievement rate moved: v0 = 50%, v1 = 100%, trend improving.
    stats_after = client.get(f"/v1/optimizer/objective/stats?agent={agent}", headers=auth).json()
    by_ver = {v["version"]: v for v in stats_after["by_directive_version"]}
    assert by_ver[0]["achievement_rate"] == 0.5
    assert by_ver[1]["achievement_rate"] == 1.0
    assert stats_after["trend"]["improving"] is True
    assert stats_after["trend"]["delta"] == 0.5

    with capsys.disabled():
        print("\n--- self-improvement loop proof ---")
        print(f"baseline (v0) achievement rate : {stats_before['achievement_rate']:.0%} "
              f"({stats_before['classified_calls']} calls)")
        print(f"optimizer produced             : standing v{body['version']} — {body['rationale']}")
        print(f"targeted failure patterns      : {[p['pattern'] for p in body['top_failure_patterns']]}")
        print("per-directive-version rates    : " + ", ".join(
            f"v{v['version']}={v['achievement_rate']:.0%}" for v in stats_after["by_directive_version"]))
        print(f"trend                          : +{stats_after['trend']['delta']:.0%} "
              f"(improving={stats_after['trend']['improving']})")


def test_default_objective_when_unset(client):
    key = cloudapp.issue_key("default@test.dev", plan="pro", source="admin", grant_seconds=1000)
    r = client.get("/v1/optimizer/objective?agent=builder", headers={"Authorization": f"Bearer {key}"})
    assert r.status_code == 200
    body = r.json()
    assert body["is_default"] is True
    assert {c["name"] for c in body["objective"]["criteria"]} == {
        "intent_satisfied", "no_hallucinated_facts", "actions_verified", "appropriate_tone"
    }


def test_improve_without_reports_is_helpful_not_fabricated(client):
    key = cloudapp.issue_key("empty@test.dev", plan="pro", source="admin", grant_seconds=1000)
    headers = {"Authorization": f"Bearer {key}"}
    r = client.post("/v1/optimizer/improve", headers=headers, json={"agent": "builder"})
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == 0
    assert body["calls_analyzed"] == 0
    assert body["unchanged"] is True
    # No new directive was fabricated.
    standing = client.get("/v1/optimizer/standing?agent=builder", headers=headers).json()
    assert standing["version"] == 0
