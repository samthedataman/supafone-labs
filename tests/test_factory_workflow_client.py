from supafone_labs import Supafone


def client_and_calls():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True}

    return Supafone(api_key="sf_test", transport=transport), calls


def workflow():
    return {
        "name": "Booking team",
        "realtime": {"provider": "google", "model": "gemini-3.1-flash-live-preview"},
        "captureFields": ["name", "reference"],
        "manager": {"enabled": True, "reasoning": "supervisor", "maxTasks": 6, "maxParallel": 2, "timeoutSeconds": 5},
        "agentTeam": {"enabled": True, "fallbackMemberId": "booker", "members": [
            {"id": "booker", "stageKeys": ["book"], "instructions": "Consult only the configured calendar.", "tools": ["check_availability"]},
        ]},
        "runtimeRouting": {"enabled": True, "allowedModels": [{"provider": "xai", "model": "grok-voice-latest", "voice": "eve"}],
                           "maxHandoffs": 1, "recoverOnDisconnect": False},
        "recording": {"enabled": True, "transcribe": True},
        "callStages": [
            {"key": "capture", "name": "Capture", "tools": ["save_lead"], "temperature": 0.2,
             "requirements": {"requiredFields": ["name"], "successfulTools": []}, "nextStages": ["book", "decline"]},
            {"key": "decline", "name": "Decline", "tools": [], "nextStages": []},
            {"key": "book", "name": "Book", "tools": ["book_appointment"], "role": "scheduling", "specialistId": "booker",
             "requirements": {"successfulTools": ["book_appointment"]}, "nextStages": []},
        ],
    }


def test_factory_create_and_patch_preserve_workflow_gates_and_explicit_empty_edges():
    client, calls = client_and_calls()
    config = workflow()
    client.labs.agents.create(config)
    client.labs.agents.update("booker", config)
    for method, _, payload in calls:
        assert method in {"POST", "PATCH"}
        assert payload["manager"] == {"enabled": True, "reasoning": "supervisor", "max_tasks": 6, "max_parallel": 2, "timeout_seconds": 5}
        assert payload["agent_team"]["members"][0]["stage_keys"] == ["book"]
        assert payload["runtime_routing"]["recover_on_disconnect"] is False
        assert payload["runtime_routing"]["allowed_models"][0]["provider"] == "xai"
        assert payload["recording"] == {"enabled": True, "transcribe": True}
        assert payload["capture_fields"] == ["name", "reference"]
        stages = payload["call_stages"]
        assert stages[0]["temperature"] == 0.2
        assert stages[0]["requirements"] == {"required_fields": ["name"], "successful_tools": []}
        assert stages[1]["next_stages"] == [] and stages[1]["tools"] == []
        assert stages[2]["specialist_id"] == "booker" and stages[2]["role"] == "scheduling"


def test_workflow_patch_can_disable_features_without_injecting_creation_defaults():
    client, calls = client_and_calls()
    client.labs.agents.update("booker", manager=False, recording={"enabled": False, "transcribe": False},
                              runtime_routing={"enabled": False, "allowed_models": []})
    payload = calls[0][2]
    assert payload == {"manager": False, "recording": {"enabled": False, "transcribe": False},
                       "runtime_routing": {"enabled": False, "allowed_models": []}}


def test_plan_request_normalizes_stage_gate_aliases_and_excludes_manager_profiles():
    client, calls = client_and_calls()
    config = workflow()
    config["supervisor"] = {"mode": "byok", "api_key": "must-not-enter-planner"}
    client.labs.agents.plan(config)
    payload = calls[0][2]
    assert payload["call_stages"][1]["next_stages"] == []
    assert payload["call_stages"][0]["requirements"]["required_fields"] == ["name"]
    assert "manager" not in payload and "supervisor" not in payload
    assert "must-not-enter-planner" not in str(payload)


def test_boolean_recording_and_language_allowlist_survive_wire_serialization():
    client, calls = client_and_calls()
    client.labs.agents.update("booker", recording=False, timezone="America/New_York", timeAwareness=False,
                              runtimeRouting={"enabled": True, "allowedLanguages": ["en"]})
    assert calls[0][2] == {"recording": False, "timezone": "America/New_York", "time_awareness": False,
                           "runtime_routing": {"enabled": True, "allowed_languages": ["en"]}}
