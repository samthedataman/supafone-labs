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
        {"api_key": "sf_test", "supafone_api_base_url": "https://api.supafone.ai"},
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
