from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "supafone_mcp.py"
SPEC = importlib.util.spec_from_file_location("supafone_mcp", MODULE_PATH)
assert SPEC and SPEC.loader
supafone_mcp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supafone_mcp)


def test_initialize_and_list_tools():
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)

    init = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        }
    )
    assert init["result"]["serverInfo"]["name"] == "supafone-labs-mcp"

    listed = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tool_names = {tool["name"] for tool in listed["result"]["tools"]}
    assert {
        "create_inbound_agent",
        "create_outbound_agent",
        "create_inbound_agent_with_number",
        "create_outbound_agent_with_number",
        "get_usage",
        "get_tester_capabilities",
        "test_phone_agent",
        "get_phone_test",
        "wait_for_phone_test",
        "generate_qa_scenarios",
        "list_qa_runs",
        "run_watcher_qa",
        "list_logs",
        "tail_logs",
        "poll_logs",
    }.issubset(tool_names)


def test_create_inbound_agent_uses_python_sdk(monkeypatch):
    calls = []

    class FakeAgents:
        def create_inbound(self, config):
            calls.append(("create_inbound", config))
            return {"success": True, "agent": {"agent_key": config["agentKey"]}}

    class FakeLabs:
        def __init__(self):
            self.agents = FakeAgents()

    class FakeSupafone:
        def __init__(self, **kwargs):
            calls.append(("client", kwargs))
            self.labs = FakeLabs()

    monkeypatch.setattr(supafone_mcp, "Supafone", FakeSupafone)

    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    result = server.call_tool(
        "create_inbound_agent",
        {
            "apiKey": "sf_test",
            "agentKey": "northline-intake",
            "name": "Northline intake",
            "labs": {"enabled": True},
        },
    )

    assert result["agent"]["agent_key"] == "northline-intake"
    assert calls[0] == (
        "client",
        {
            "api_key": "sf_test",
            "labs_api_key": "sf_test",
            "supafone_api_base_url": "https://api.supafone.ai",
            "labs_api_base_url": "https://api.labs.supafone.ai",
        },
    )
    assert calls[1] == (
        "create_inbound",
        {
            "agentKey": "northline-intake",
            "name": "Northline intake",
            "labs": {"enabled": True},
        },
    )


def test_poll_logs_returns_bounded_batches(monkeypatch):
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    responses = [
        {"logs": [{"at": "2026-07-08T01:00:00Z", "endpoint": "oracle", "detail": "first"}]},
        {
            "logs": [
                {"at": "2026-07-08T01:00:01Z", "endpoint": "tts", "detail": "second"},
                {"at": "2026-07-08T01:00:00Z", "endpoint": "oracle", "detail": "first"},
            ]
        },
    ]

    def fake_labs_get(path, arguments):
        assert path == "/v1/logs?limit=50"
        assert arguments["apiKey"] == "sl_test"
        return responses.pop(0)

    monkeypatch.setattr(server, "_labs_get", fake_labs_get)

    result = server.call_tool(
        "tail_logs",
        {"apiKey": "sl_test", "limit": 50, "iterations": 2, "intervalSeconds": 0.5},
    )

    assert result["polling"]["iterations"] == 2
    assert result["batches"][0]["new_logs"][0]["detail"] == "first"
    assert result["batches"][1]["new_logs"][0]["detail"] == "second"
    assert result["latest_logs"][0]["detail"] == "second"


def test_phone_agent_requires_authorization_and_preserves_provider_metadata(monkeypatch):
    calls = []

    class FakeTester:
        def call(self, **kwargs):
            calls.append(kwargs)
            return {"session_id": "ts_123", "status": "dialing"}

    class FakeSupafone:
        def __init__(self, **_kwargs):
            self.tester = FakeTester()

    monkeypatch.setattr(supafone_mcp, "Supafone", FakeSupafone)
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)

    denied = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "test_phone_agent",
                "arguments": {"apiKey": "sl_test", "toNumber": "+14155550100", "authorized": False},
            },
        }
    )
    assert denied["result"]["isError"] is True

    result = server.call_tool(
        "test_phone_agent",
        {
            "apiKey": "sl_test",
            "toNumber": "+14155550100",
            "scenario": "language_switch",
            "aiProvider": "grok",
            "telephonyProvider": "telnyx",
            "authorized": True,
        },
    )
    assert result["session_id"] == "ts_123"
    assert calls == [
        {
            "to_number": "+14155550100",
            "scenario": "language_switch",
            "agent_label": "mcp-tester",
            "ai_provider": "grok",
            "telephony_provider": "telnyx",
            "authorized": True,
        }
    ]


# ---------------------------------------------------------------------------
# Main-app tools: campaigns + place_call (JWT auth against api.supafone.ai)
# ---------------------------------------------------------------------------

def test_tools_list_includes_campaign_and_call_tools():
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    listed = server.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
    tool_names = {tool["name"] for tool in listed["result"]["tools"]}
    assert {
        "place_call",
        "list_voice_agents",
        "list_campaigns",
        "create_campaign",
        "get_campaign",
        "update_campaign",
        "add_campaign_recipients",
        "list_campaign_recipients",
        "launch_campaign",
        "pause_campaign",
        "list_campaign_presets",
        "apply_campaign_preset",
        "create_sign_link",
    }.issubset(tool_names)


def _fake_main_http(requests_log, responses):
    def fake(method, url, payload, token):
        requests_log.append({"method": method, "url": url, "payload": payload, "token": token})
        return responses.pop(0)

    return fake


def test_place_call_dials_through_phone_endpoint(monkeypatch):
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    log = []
    monkeypatch.setattr(
        server,
        "_main_http",
        _fake_main_http(log, [(200, {"success": True, "call_sid": "CA123", "provider": "native"})]),
    )

    result = server.call_tool(
        "place_call",
        {"token": "jwt-abc", "agentId": "agent-1", "toNumber": "+15551234567"},
    )

    assert result["success"] is True and result["call_sid"] == "CA123"
    assert log == [
        {
            "method": "POST",
            "url": "https://api.supafone.ai/api/v1/phone/test-call",
            "payload": {"agent_id": "agent-1", "to_number": "+15551234567"},
            "token": "jwt-abc",
        }
    ]


def test_place_call_requires_agent_and_number():
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    for arguments in ({"token": "t", "toNumber": "+15551234567"}, {"token": "t", "agentId": "a"}):
        response = server.handle(
            {"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": "place_call", "arguments": arguments}}
        )
        assert response["result"]["isError"] is True


def test_campaign_flow_create_add_launch(monkeypatch):
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    log = []
    monkeypatch.setattr(
        server,
        "_main_http",
        _fake_main_http(
            log,
            [
                (200, {"campaign": {"id": "c1", "name": "Chase", "status": "draft"}}),
                (200, {"added": 1, "stats": {}}),
                (200, {"campaign": {"id": "c1", "status": "active"}}),
            ],
        ),
    )

    created = server.call_tool(
        "create_campaign", {"token": "jwt", "name": "Chase", "goal": "book", "agentId": "agent-1"}
    )
    assert created["campaign"]["id"] == "c1"
    added = server.call_tool(
        "add_campaign_recipients",
        {
            "token": "jwt",
            "campaignId": "c1",
            "recipients": [{"name": "Jane", "phone": "+15550001111", "outreach_consent": "yes"}],
        },
    )
    assert added["added"] == 1
    launched = server.call_tool("launch_campaign", {"token": "jwt", "campaignId": "c1"})
    assert launched["campaign"]["status"] == "active"

    assert [entry["url"].split("api.supafone.ai")[1] for entry in log] == [
        "/api/v1/campaigns",
        "/api/v1/campaigns/c1/recipients",
        "/api/v1/campaigns/c1/launch",
    ]
    assert log[0]["payload"] == {"name": "Chase", "goal": "book", "agent_id": "agent-1"}


def test_main_api_logs_in_and_retries_once_on_401(monkeypatch):
    monkeypatch.delenv("SUPAFONE_TOKEN", raising=False)
    monkeypatch.delenv("SUPAFONE_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("SUPAFONE_JWT", raising=False)
    monkeypatch.setenv("SUPAFONE_EMAIL", "owner@real-domain.io")
    monkeypatch.setenv("SUPAFONE_PASSWORD", "hunter22!")

    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    log = []
    monkeypatch.setattr(
        server,
        "_main_http",
        _fake_main_http(
            log,
            [
                (200, {"token": "jwt-first"}),                # login
                (401, {"detail": "Token expired"}),           # campaigns with stale token
                (200, {"token": "jwt-second"}),               # re-login
                (200, {"campaigns": [{"id": "c1"}]}),          # retry succeeds
            ],
        ),
    )

    result = server.call_tool("list_campaigns", {})
    assert result["campaigns"][0]["id"] == "c1"
    assert log[0]["url"].endswith("/api/v1/auth/login") and log[0]["token"] is None
    assert log[1]["token"] == "jwt-first"
    assert log[2]["url"].endswith("/api/v1/auth/login")
    assert log[3]["token"] == "jwt-second"


def test_main_api_requires_some_auth(monkeypatch):
    for key in ("SUPAFONE_TOKEN", "SUPAFONE_ACCESS_TOKEN", "SUPAFONE_JWT", "SUPAFONE_EMAIL", "SUPAFONE_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    response = server.handle(
        {"jsonrpc": "2.0", "id": 11, "method": "tools/call", "params": {"name": "list_campaigns", "arguments": {}}}
    )
    assert response["result"]["isError"] is True
    assert "SUPAFONE_TOKEN" in response["result"]["content"][0]["text"]


def test_monitor_campaign_splits_in_flight_and_builds_links(monkeypatch):
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    log = []
    monkeypatch.setattr(
        server,
        "_main_http",
        _fake_main_http(
            log,
            [
                (
                    200,
                    {
                        "stats": {"queued": 3, "in_flight": 1},
                        "calls": [
                            {"id": "call-live", "status": "in_progress", "to_number": "+15550001111"},
                            {"id": "call-done", "status": "completed"},
                        ],
                    },
                )
            ],
        ),
    )

    result = server.call_tool("monitor_campaign", {"token": "jwt", "campaignId": "c1"})

    assert log[0]["url"].endswith("/api/v1/campaigns/c1/activity")
    assert [c["id"] for c in result["in_flight"]] == ["call-live"]
    assert result["in_flight"][0]["listen_url"] == "https://app.supafone.ai/app/calls?call=call-live"
    assert [c["id"] for c in result["recent_calls"]] == ["call-done"]
    assert result["portal_url"] == "https://app.supafone.ai/app/developer?campaign=c1"


def test_get_call_fetches_call_record(monkeypatch):
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    log = []
    monkeypatch.setattr(
        server,
        "_main_http",
        _fake_main_http(log, [(200, {"call": {"id": "call-live", "status": "in_progress", "transcript": []}})]),
    )
    result = server.call_tool("get_call", {"token": "jwt", "callId": "call-live"})
    assert result["call"]["id"] == "call-live"
    assert log[0]["url"].endswith("/api/v1/calls/call-live")


def test_set_signature_fields_merges_onto_stored_doc(monkeypatch):
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    log = []
    monkeypatch.setattr(
        server,
        "_main_http",
        _fake_main_http(
            log,
            [
                (200, {"campaign": {"id": "c1", "settings": {"native_signing": {"storedName": "d.pdf", "pdfUrl": "https://x/d.pdf"}}}}),
                (200, {"campaign": {"id": "c1"}}),
            ],
        ),
    )
    fields = [{"key": "client_signature", "type": "signature", "placement": {"page": 0, "x": 72, "y": 120, "width": 92, "height": 26}}]
    server.call_tool("set_signature_fields", {"token": "jwt", "campaignId": "c1", "fields": fields})
    assert log[1]["method"] == "PUT"
    native = log[1]["payload"]["settings"]["native_signing"]
    assert native["enabled"] is True and native["fields"] == fields and native["storedName"] == "d.pdf"


def test_upload_signing_document_reads_local_pdf(monkeypatch, tmp_path):
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    pdf = tmp_path / "retainer.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    seen = {}

    def fake_upload(path, filename, data, arguments):
        seen.update({"path": path, "filename": filename, "size": len(data)})
        return {"campaign": {}, "detected_fields": [{"type": "signature"}]}

    monkeypatch.setattr(server, "_main_upload", lambda path, *, filename, data, arguments: fake_upload(path, filename, data, arguments))
    result = server.call_tool("upload_signing_document", {"token": "jwt", "campaignId": "c1", "filePath": str(pdf)})
    assert result["detected_fields"][0]["type"] == "signature"
    assert seen == {"path": "/api/v1/campaigns/c1/signing/document", "filename": "retainer.pdf", "size": 13}


# ---------------------------------------------------------------------------
# Brand scan + intake generation + campaign-as-code tools
# ---------------------------------------------------------------------------

def test_tools_list_includes_brand_intake_and_config_tools():
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    listed = server.handle({"jsonrpc": "2.0", "id": 20, "method": "tools/list"})
    tool_names = {tool["name"] for tool in listed["result"]["tools"]}
    assert {
        "scan_brand",
        "generate_intake_form",
        "apply_campaign_config",
        "export_campaign_config",
        "generate_campaign_config",
    }.issubset(tool_names)


def test_scan_brand_posts_url(monkeypatch):
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    log = []
    monkeypatch.setattr(
        server,
        "_main_http",
        _fake_main_http(
            log,
            [(200, {"business_name": "Acme Dental", "colors": ["#1a2b3c"], "logo_url": "https://a/l.svg"})],
        ),
    )

    result = server.call_tool("scan_brand", {"token": "jwt", "url": "https://acme.example"})

    assert result["business_name"] == "Acme Dental"
    assert log == [
        {
            "method": "POST",
            "url": "https://api.supafone.ai/api/v1/agents/brand-scan",
            "payload": {"url": "https://acme.example"},
            "token": "jwt",
        }
    ]


def test_scan_brand_requires_url():
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    response = server.handle(
        {"jsonrpc": "2.0", "id": 21, "method": "tools/call", "params": {"name": "scan_brand", "arguments": {"token": "t"}}}
    )
    assert response["result"]["isError"] is True


def test_generate_intake_form_unscoped_and_agent_scoped(monkeypatch):
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    log = []
    monkeypatch.setattr(
        server,
        "_main_http",
        _fake_main_http(
            log,
            [
                (200, {"intake": {"script": []}, "generated": True, "applied": False}),
                (200, {"intake": {"script": []}, "generated": True, "applied": True}),
            ],
        ),
    )

    server.call_tool(
        "generate_intake_form",
        {"token": "jwt", "description": "Collect roof type", "industry": "roofing"},
    )
    applied = server.call_tool(
        "generate_intake_form",
        {"token": "jwt", "description": "Collect roof type", "agentId": "ag1", "apply": True},
    )

    assert applied["applied"] is True
    assert log[0]["url"].endswith("/api/v1/agents/generate-intake")
    assert log[0]["payload"] == {"description": "Collect roof type", "industry": "roofing"}
    assert log[1]["url"].endswith("/api/v1/agents/ag1/generate-intake")
    assert log[1]["payload"] == {"description": "Collect roof type", "apply": True}


def test_generate_intake_form_apply_requires_agent():
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 22,
            "method": "tools/call",
            "params": {
                "name": "generate_intake_form",
                "arguments": {"token": "t", "description": "x", "apply": True},
            },
        }
    )
    assert response["result"]["isError"] is True
    assert "agentId" in response["result"]["content"][0]["text"]


def test_apply_campaign_config_validates_then_applies(monkeypatch):
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    log = []
    monkeypatch.setattr(
        server,
        "_main_http",
        _fake_main_http(
            log,
            [
                (200, {"valid": True, "errors": [], "warnings": [], "summary": {"slug": "s"}}),
                (200, {"campaign": {"id": "c1"}, "created": True, "launched": False}),
            ],
        ),
    )

    doc = "version: 1\ncampaign:\n  slug: spring-follow-up\n"
    result = server.call_tool(
        "apply_campaign_config", {"token": "jwt", "config": doc, "launch": False}
    )

    assert result["created"] is True
    assert log[0]["url"].endswith("/api/v1/campaigns/config/validate")
    assert log[1]["url"].endswith("/api/v1/campaigns/config/apply")
    assert log[0]["payload"] == {"config": doc, "launch": False}
    assert log[1]["payload"] == {"config": doc, "launch": False}


def test_apply_campaign_config_surfaces_validation_errors_without_applying(monkeypatch):
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    log = []
    monkeypatch.setattr(
        server,
        "_main_http",
        _fake_main_http(
            log,
            [(200, {"valid": False, "errors": ["campaign.slug: required"], "warnings": []})],
        ),
    )

    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 23,
            "method": "tools/call",
            "params": {
                "name": "apply_campaign_config",
                "arguments": {"token": "jwt", "config": "version: 1\ncampaign: {}\n"},
            },
        }
    )

    assert response["result"]["isError"] is True
    assert "campaign.slug: required" in response["result"]["content"][0]["text"]
    assert len(log) == 1  # only the validate call — nothing was applied


def test_apply_campaign_config_reads_local_file(monkeypatch, tmp_path):
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    doc = tmp_path / "campaign.yaml"
    doc.write_text("version: 1\ncampaign:\n  slug: from-file\n", encoding="utf-8")
    log = []
    monkeypatch.setattr(
        server,
        "_main_http",
        _fake_main_http(
            log,
            [
                (200, {"valid": True, "errors": [], "warnings": [], "summary": {}}),
                (200, {"campaign": {"id": "c2"}, "created": True}),
            ],
        ),
    )

    server.call_tool("apply_campaign_config", {"token": "jwt", "filePath": str(doc)})

    assert log[0]["payload"]["config"] == "version: 1\ncampaign:\n  slug: from-file\n"


def test_apply_campaign_config_requires_config_or_file():
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    for arguments in ({"token": "t"}, {"token": "t", "filePath": "/nope/missing.yaml"}):
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 24,
                "method": "tools/call",
                "params": {"name": "apply_campaign_config", "arguments": arguments},
            }
        )
        assert response["result"]["isError"] is True


def test_export_campaign_config_fetches_document(monkeypatch):
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    log = []
    monkeypatch.setattr(
        server,
        "_main_http",
        _fake_main_http(log, [(200, {"config": "version: 1\n", "format": "yaml", "slug": "s"})]),
    )

    result = server.call_tool("export_campaign_config", {"token": "jwt", "campaignId": "c1"})

    assert result["format"] == "yaml"
    assert log[0]["method"] == "GET"
    assert log[0]["url"].endswith("/api/v1/campaigns/c1/config")


def test_generate_campaign_config_posts_prompt_csv_and_agent(monkeypatch):
    server = supafone_mcp.SupafoneMCPServer(sleep=lambda _seconds: None)
    log = []
    monkeypatch.setattr(
        server,
        "_main_http",
        _fake_main_http(log, [(200, {"config": "version: 1\n", "format": "yaml", "generated": True})]),
    )

    result = server.call_tool(
        "generate_campaign_config",
        {
            "token": "jwt",
            "prompt": "Win back stale roofing quotes",
            "csv": "name,phone\nJane,+14155550123\n",
            "agentId": "ag1",
        },
    )

    assert result["generated"] is True
    assert log[0]["url"].endswith("/api/v1/campaigns/config/generate")
    assert log[0]["payload"] == {
        "prompt": "Win back stale roofing quotes",
        "csv": "name,phone\nJane,+14155550123\n",
        "agent_id": "ag1",
    }
