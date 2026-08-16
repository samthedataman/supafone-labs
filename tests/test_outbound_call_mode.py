import pytest

from supafone_labs import (
    OUTBOUND_CALL_MODE_BOUNDS,
    OUTBOUND_CALL_MODE_PROVIDER_MATRIX,
    Supafone,
    outbound_call_mode_provider_profile,
    outbound_call_mode_readiness,
)


def _agent_client(calls):
    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"success": True, "agent": {"agent_key": "ivr-agent"}, "runtime": {}}

    return Supafone(api_key="sf_test", transport=transport)


def test_outbound_call_mode_is_omitted_by_default_and_disabled_is_minimal():
    calls = []
    sf = _agent_client(calls)

    sf.labs.agents.create_outbound({"name": "Legacy outbound"})
    sf.labs.agents.create_outbound(
        {"name": "Explicitly disabled", "outbound_call_mode": {"enabled": False}}
    )

    assert "metadata" not in calls[0][2]
    assert calls[1][2]["metadata"]["outbound_call_mode"] == {
        "version": 1,
        "enabled": False,
    }


def test_outbound_call_mode_serializes_canonical_defaults_and_preserves_metadata():
    calls = []
    sf = _agent_client(calls)

    sf.labs.agents.create_outbound(
        {
            "name": "Claims follow-up",
            "metadata": {"tenant_label": "north"},
            "outbound_call_mode": {
                "enabled": True,
                "observability": {"metadata": {"workflow": "claims"}},
            },
        }
    )

    metadata = calls[0][2]["metadata"]
    assert metadata["tenant_label"] == "north"
    mode = metadata["outbound_call_mode"]
    assert mode == {
        "version": 1,
        "enabled": True,
        "initial_mode": "mission",
        "ivr_mode": "dynamic",
        "transport_scope": "provider_agnostic",
        "capability_policy": "fail_closed",
        "auto_detect": True,
        "dtmf_tool_enabled": True,
        "max_duration_seconds": 180,
        "max_keypresses": 12,
        "repeated_menu_limit": 3,
        "no_progress_timeout_seconds": 30,
        "human_detection_enabled": True,
        "resume_on_human": True,
        "observability": {
            "enabled": True,
            "include_trigger": True,
            "include_transitions": True,
            "include_termination_reason": True,
            "metadata": {"workflow": "claims"},
        },
        "required_capabilities": [
            "dtmf",
            "state_persistence",
            "human_detection",
            "observability",
        ],
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_duration_seconds", 29),
        ("max_duration_seconds", 901),
        ("max_keypresses", 0),
        ("max_keypresses", 65),
        ("repeated_menu_limit", 0),
        ("repeated_menu_limit", 11),
        ("no_progress_timeout_seconds", 4),
        ("no_progress_timeout_seconds", 121),
    ],
)
def test_outbound_call_mode_rejects_values_outside_canonical_bounds(field, value):
    sf = _agent_client([])
    with pytest.raises(ValueError, match=field):
        sf.labs.agents.create_outbound(
            {"name": "Invalid limits", "outbound_call_mode": {"enabled": True, field: value}}
        )


def test_provider_matrix_contains_all_public_transports_and_aliases():
    assert OUTBOUND_CALL_MODE_BOUNDS == {
        "max_duration_seconds": {"default": 180, "min": 30, "max": 900},
        "max_keypresses": {"default": 12, "min": 1, "max": 64},
        "repeated_menu_limit": {"default": 3, "min": 1, "max": 10},
        "no_progress_timeout_seconds": {"default": 30, "min": 5, "max": 120},
    }
    expected = {
        "supafone_managed": "supafone_managed",
        "byo_twilio": "twilio",
        "byo_telnyx": "telnyx",
        "byo_plivo": "plivo",
        "signal_wire": "signalwire",
        "custom_sip": "sip_byoc",
    }
    assert set(OUTBOUND_CALL_MODE_PROVIDER_MATRIX) == {
        "supafone_managed",
        "twilio",
        "telnyx",
        "plivo",
        "signalwire",
        "sip_byoc",
    }
    for alias, family in expected.items():
        profile = outbound_call_mode_provider_profile(alias)
        assert profile["transport_family"] == family
        assert profile["execution"] == "adapter_runtime_dependent"
        assert profile["capability_policy"] == "fail_closed"


def test_telnyx_ready_and_adapter_fail_closed_cases_do_not_infer_from_provider():
    config = {"enabled": True}
    ready = outbound_call_mode_readiness(
        config,
        {
            "provider": "telnyx",
            "dtmf": True,
            "state_persistence": True,
            "human_detection": True,
            "observability": True,
        },
    )
    assert ready["ready"] is True
    assert ready["status"] == "ready"
    assert ready["transport_family"] == "telnyx"

    unsupported = outbound_call_mode_readiness(
        config,
        {
            "provider": "signalwire",
            "dtmf": False,
            "state_persistence": True,
            "human_detection": True,
            "observability": True,
        },
    )
    assert unsupported["ready"] is False
    assert unsupported["status"] == "unsupported"
    assert unsupported["unsupported_capabilities"] == ["dtmf"]

    unknown = outbound_call_mode_readiness(config, {"provider": "twilio"})
    assert unknown["ready"] is False
    assert unknown["status"] == "unknown"
    assert "dtmf" in unknown["missing_capabilities"]

    custom_ready = outbound_call_mode_readiness(
        config,
        {
            "provider": "unlisted_adapter",
            "dtmf": True,
            "state_persistence": True,
            "human_detection": True,
            "observability": True,
        },
    )
    assert custom_ready["ready"] is True
    assert custom_ready["transport_family"] == "unknown"


def test_agent_lifecycle_routes_and_update_persist_mode_in_metadata():
    calls = []
    sf = _agent_client(calls)

    sf.labs.agents.update(
        "agent/one",
        {
            "metadata": {"owner": "ops"},
            "outboundCallMode": {"enabled": True, "max_keypresses": 20},
        },
        agencyId="agency-1",
    )
    sf.labs.agents.readiness("agent/one", agencyId="agency-1")
    sf.labs.agents.activate("agent/one", agencyId="agency-1")
    sf.labs.agents.pause("agent/one", agencyId="agency-1")

    assert [call[:2] for call in calls] == [
        ("PATCH", "/api/v1/labs/agents/agent/one?agency_id=agency-1"),
        ("GET", "/api/v1/labs/agents/agent/one/readiness?agency_id=agency-1"),
        ("POST", "/api/v1/labs/agents/agent/one/activate?agency_id=agency-1"),
        ("POST", "/api/v1/labs/agents/agent/one/pause?agency_id=agency-1"),
    ]
    assert calls[0][2]["metadata"]["owner"] == "ops"
    assert calls[0][2]["metadata"]["outbound_call_mode"]["max_keypresses"] == 20


def test_campaign_create_and_update_persist_outbound_call_mode_in_settings():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"campaign": {"id": "campaign-1", "settings": payload or {}}}

    sf = Supafone(token="jwt-test", transport=transport)
    sf.campaigns.create(
        name="IVR follow-up",
        settings={"timezone": "America/New_York"},
        outbound_call_mode={"enabled": True},
    )
    sf.campaigns.update(
        "campaign-1",
        settings={"cadence_label": "weekday"},
        outboundCallMode={"enabled": False},
    )

    assert calls[0] == (
        "POST",
        "/api/v1/campaigns",
        {"name": "IVR follow-up", "goal": "book"},
    )
    assert calls[1][0:2] == ("PUT", "/api/v1/campaigns/campaign-1")
    assert calls[1][2]["settings"]["timezone"] == "America/New_York"
    assert calls[1][2]["settings"]["outbound_call_mode"]["transport_scope"] == (
        "provider_agnostic"
    )
    assert calls[2][2]["settings"] == {
        "cadence_label": "weekday",
        "outbound_call_mode": {"version": 1, "enabled": False},
    }


def test_campaign_create_without_settings_keeps_single_legacy_request():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"campaign": {"id": "campaign-1"}}

    Supafone(token="jwt-test", transport=transport).campaigns.create(name="Legacy")

    assert calls == [
        ("POST", "/api/v1/campaigns", {"name": "Legacy", "goal": "book"})
    ]
