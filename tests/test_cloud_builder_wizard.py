"""Builder wizard endpoint — the hybrid conversational agent builder.

Contract under test: the oracle only MAPS prose onto the caller's field
catalog; the endpoint re-validates every value against that catalog (a model
that hallucinates a field or option gets silently clamped), the response
schema never varies, and oracle failure degrades to {"fallback": true}.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile

from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="sl_cloud_wizard_test_")
_SAVED_DATA_DIR = os.environ.get("DATA_DIR")
os.environ["DATA_DIR"] = _TMP

_APP_PATH = os.path.join(os.path.dirname(__file__), "..", "cloud", "app.py")
_spec = importlib.util.spec_from_file_location("supafone_labs_cloud_wizard_app", _APP_PATH)
cloudapp = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cloudapp
_spec.loader.exec_module(cloudapp)

if _SAVED_DATA_DIR is None:
    os.environ.pop("DATA_DIR", None)
else:
    os.environ["DATA_DIR"] = _SAVED_DATA_DIR


FIELDS = [
    {"key": "direction", "label": "Direction", "type": "choice", "options": ["inbound", "outbound"]},
    {"key": "agentRecipe", "label": "Agent type", "type": "choice", "options": ["receptionist", "sales", "support"]},
    {"key": "businessName", "label": "Business", "type": "text", "options": []},
    {"key": "tools", "label": "Tools", "type": "multi", "options": ["scheduling", "sms", "voicemail"]},
]


def _key(client: TestClient) -> str:
    import uuid

    registered = client.post(
        "/v1/auth/register",
        json={"email": f"wizard-{uuid.uuid4().hex[:10]}@example.com", "password": "password123"},
    )
    assert registered.status_code == 200, registered.text
    token = registered.json()["token"]
    account = client.get("/v1/account", headers={"Authorization": f"Bearer {token}"})
    return account.json()["keys"][0]["key"]


def test_wizard_validates_updates_against_catalog(monkeypatch):
    client = TestClient(cloudapp.app)
    key = _key(client)

    async def fake_complete(model, body):
        return {
            "text": (
                '{"updates": {"direction": "outbound", "agentRecipe": "sales", '
                '"businessName": "Acme Roofing", "tools": ["sms", "not_a_tool"], '
                '"hallucinated_field": "x", "direction2": "inbound"}, '
                '"reply": "Outbound sales agent for Acme Roofing — nice."}'
            ),
            "model": model,
            "usage": {},
        }

    monkeypatch.setattr(cloudapp, "_anthropic_complete", fake_complete)
    monkeypatch.setattr(cloudapp, "ANTHROPIC_API_KEY", "test-key")

    res = client.post(
        "/v1/builder/wizard",
        headers={"Authorization": f"Bearer {key}"},
        json={"message": "outbound sales agent for Acme Roofing with texting", "draft": {}, "fields": FIELDS},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["fallback"] is False
    # Hallucinated keys dropped; off-catalog multi values filtered.
    assert data["updates"] == {
        "direction": "outbound",
        "agentRecipe": "sales",
        "businessName": "Acme Roofing",
        "tools": ["sms"],
    }
    assert "Acme Roofing" in data["reply"]


def test_wizard_rejects_off_catalog_choice(monkeypatch):
    client = TestClient(cloudapp.app)
    key = _key(client)

    async def fake_complete(model, body):
        return {"text": '{"updates": {"direction": "sideways"}, "reply": "ok"}', "model": model, "usage": {}}

    monkeypatch.setattr(cloudapp, "_anthropic_complete", fake_complete)
    monkeypatch.setattr(cloudapp, "ANTHROPIC_API_KEY", "test-key")

    res = client.post(
        "/v1/builder/wizard",
        headers={"Authorization": f"Bearer {key}"},
        json={"message": "go sideways", "draft": {}, "fields": FIELDS},
    )
    assert res.status_code == 200
    assert res.json()["updates"] == {}


def test_wizard_degrades_to_fallback_without_oracle(monkeypatch):
    client = TestClient(cloudapp.app)
    key = _key(client)
    monkeypatch.setattr(cloudapp, "ANTHROPIC_API_KEY", "")

    res = client.post(
        "/v1/builder/wizard",
        headers={"Authorization": f"Bearer {key}"},
        json={"message": "anything", "draft": {}, "fields": FIELDS},
    )
    assert res.status_code == 200
    assert res.json() == {"updates": {}, "reply": "", "fallback": True}


def test_wizard_degrades_to_fallback_on_oracle_error(monkeypatch):
    client = TestClient(cloudapp.app)
    key = _key(client)

    async def broken_complete(model, body):
        raise RuntimeError("upstream down")

    monkeypatch.setattr(cloudapp, "_anthropic_complete", broken_complete)
    monkeypatch.setattr(cloudapp, "ANTHROPIC_API_KEY", "test-key")

    res = client.post(
        "/v1/builder/wizard",
        headers={"Authorization": f"Bearer {key}"},
        json={"message": "anything", "draft": {}, "fields": FIELDS},
    )
    assert res.status_code == 200
    assert res.json()["fallback"] is True


def test_wizard_requires_fields_catalog(monkeypatch):
    client = TestClient(cloudapp.app)
    key = _key(client)
    res = client.post(
        "/v1/builder/wizard",
        headers={"Authorization": f"Bearer {key}"},
        json={"message": "hello", "draft": {}, "fields": []},
    )
    assert res.status_code == 422
