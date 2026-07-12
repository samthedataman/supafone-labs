"""Campaigns namespace + account auth on the Supafone client.

Same fake-transport seam as test_hosted_agents_client.py: every campaign/call
method must emit the exact (method, path, payload) tuple for the product API.
"""
from __future__ import annotations

import io
import json

import pytest

import supafone_labs.client as client_module
from supafone_labs import Supafone, SupafoneError


def _client_with_transport(calls, response=None):
    def transport(method, path, payload):
        calls.append((method, path, payload))
        return response if response is not None else {"success": True}

    return Supafone(token="jwt-test", transport=transport)


def test_account_auth_alone_is_enough_to_construct():
    supafone = Supafone(token="jwt-test", transport=lambda m, p, b: {})
    assert supafone.campaigns is not None
    with pytest.raises(ValueError):
        Supafone()  # no api key, no token, no email/password


def test_campaign_crud_routes():
    calls = []
    sf = _client_with_transport(calls, {"campaign": {"id": "c1"}, "campaigns": [], "presets": []})

    sf.campaigns.list()
    sf.campaigns.create(name="Win-back", goal="reengage", agent_id="agent-1")
    sf.campaigns.get("c1")
    sf.campaigns.update("c1", email_subject="Hi", settings={"caller_id_number": "+15550009999"})
    sf.campaigns.add_recipients("c1", [{"name": "Jane", "phone": "+15551234567", "outreach_consent": "yes"}])
    sf.campaigns.recipients("c1")
    sf.campaigns.launch("c1")
    sf.campaigns.pause("c1")
    sf.campaigns.apply_preset("c1", "win_back")
    sf.campaigns.stats("c1")
    sf.campaigns.activity("c1")
    sf.campaigns.create_sign_link("c1", "r1", title="Review & sign")

    assert [(m, p) for m, p, _ in calls] == [
        ("GET", "/api/v1/campaigns"),
        ("POST", "/api/v1/campaigns"),
        ("GET", "/api/v1/campaigns/c1"),
        ("PUT", "/api/v1/campaigns/c1"),
        ("POST", "/api/v1/campaigns/c1/recipients"),
        ("GET", "/api/v1/campaigns/c1/recipients"),
        ("POST", "/api/v1/campaigns/c1/launch"),
        ("POST", "/api/v1/campaigns/c1/pause"),
        ("POST", "/api/v1/campaigns/c1/apply-preset"),
        ("GET", "/api/v1/campaigns/c1/stats"),
        ("GET", "/api/v1/campaigns/c1/activity"),
        ("POST", "/api/v1/campaigns/c1/recipients/r1/sign-link"),
    ]
    assert calls[1][2] == {"name": "Win-back", "goal": "reengage", "agent_id": "agent-1"}
    assert calls[3][2] == {"email_subject": "Hi", "settings": {"caller_id_number": "+15550009999"}}
    assert calls[8][2] == {"preset_id": "win_back"}


def test_place_call_and_agent_listing_routes():
    calls = []
    sf = _client_with_transport(calls, {"success": True, "agents": []})
    sf.place_call(agent_id="agent-1", to_number="+15551234567")
    sf.list_voice_agents()
    assert calls == [
        ("POST", "/api/v1/phone/test-call", {"agent_id": "agent-1", "to_number": "+15551234567"}),
        ("GET", "/api/v1/agents", None),
    ]
    with pytest.raises(SupafoneError):
        sf.place_call(agent_id="agent-1")  # missing number


def test_live_builds_listen_and_portal_links():
    calls = []
    sf = _client_with_transport(
        calls,
        {
            "stats": {"queued": 1},
            "calls": [
                {"id": "call-live", "status": "in_progress"},
                {"id": "call-done", "status": "completed"},
            ],
        },
    )
    live = sf.campaigns.live("c1")
    assert calls[0][:2] == ("GET", "/api/v1/campaigns/c1/activity")
    assert [c["id"] for c in live["in_flight"]] == ["call-live"]
    assert live["in_flight"][0]["listen_url"] == "https://app.supafone.ai/app/calls?call=call-live"
    assert live["portal_url"] == "https://app.supafone.ai/app/developer?campaign=c1"


def test_account_api_logs_in_lazily_and_retries_once_on_401(monkeypatch):
    responses = [
        (200, {"token": "jwt-first"}),        # login
        (401, {"detail": "Token expired"}),   # first attempt
        (200, {"token": "jwt-second"}),       # re-login
        (200, {"campaigns": [{"id": "c1"}]}),  # retry succeeds
    ]
    seen = []

    class FakeResponse(io.BytesIO):
        def __init__(self, payload: bytes):
            super().__init__(payload)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=0):
        status, body = responses.pop(0)
        seen.append(
            {
                "url": req.full_url,
                "auth": req.get_header("Authorization"),
                "body": json.loads(req.data.decode()) if req.data else None,
            }
        )
        if status >= 400:
            raise client_module.error.HTTPError(
                req.full_url, status, "err", hdrs=None, fp=io.BytesIO(json.dumps(body).encode())
            )
        return FakeResponse(json.dumps(body).encode())

    monkeypatch.setattr(client_module.request, "urlopen", fake_urlopen)
    for key in ("SUPAFONE_TOKEN", "SUPAFONE_ACCESS_TOKEN"):
        monkeypatch.delenv(key, raising=False)

    sf = Supafone(email="owner@real-domain.io", password="hunter22!")
    result = sf.campaigns.list()

    assert result["campaigns"][0]["id"] == "c1"
    assert seen[0]["url"].endswith("/api/v1/auth/login") and seen[0]["auth"] is None
    assert seen[1]["auth"] == "Bearer jwt-first"
    assert seen[2]["url"].endswith("/api/v1/auth/login")
    assert seen[3]["auth"] == "Bearer jwt-second"


def test_signing_document_flow(tmp_path):
    calls = []
    pdf = tmp_path / "retainer.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    sf = _client_with_transport(
        calls,
        {
            "campaign": {"id": "c1", "settings": {"native_signing": {"pdfUrl": "https://x/doc.pdf", "storedName": "d.pdf"}}},
            "fields": [], "detected": False, "asset": {},
        },
    )
    sf.campaigns.upload_signing_document("c1", str(pdf))
    sf.campaigns.detect_signature_fields("c1")
    sf.campaigns.set_signature_fields(
        "c1",
        [{"key": "client_signature", "type": "signature", "placement": {"page": 0, "x": 72, "y": 120, "width": 92, "height": 26}}],
    )
    assert calls[0][:2] == ("UPLOAD", "/api/v1/campaigns/c1/signing/document")
    assert calls[0][2]["filename"] == "retainer.pdf"
    assert calls[1][:2] == ("POST", "/api/v1/campaigns/c1/signing/detect-fields")
    assert calls[2][:2] == ("GET", "/api/v1/campaigns/c1")
    method, path, payload = calls[3]
    assert (method, path) == ("PUT", "/api/v1/campaigns/c1")
    native = payload["settings"]["native_signing"]
    assert native["enabled"] is True and native["fields"][0]["key"] == "client_signature"
    assert native["storedName"] == "d.pdf"  # merge preserved the stored doc
