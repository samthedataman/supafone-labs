from supafone_labs import Supafone, outbound_call_mode_readiness


sf = Supafone(api_key="sf_live_replace_me")

readiness = outbound_call_mode_readiness(
    {"enabled": True},
    {
        "provider": "telnyx",
        "dtmf": True,
        "state_persistence": True,
        "human_detection": True,
        "observability": True,
    },
)
if not readiness["ready"]:
    raise RuntimeError(f"Outbound IVR adapter is not ready: {readiness['reasons']}")

sf.labs.agents.create_outbound(
    {
        "name": "Benefits verification",
        "outbound_call_mode": {
            "enabled": True,
            "max_duration_seconds": 180,
            "max_keypresses": 12,
        },
    }
)
