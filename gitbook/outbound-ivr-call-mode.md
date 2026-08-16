# Outbound IVR call mode

Supafone Labs `0.5.0` gives any outbound hosted agent or campaign an opt-in phone-tree navigation contract without exposing private detection or runtime implementation.

```ts
await sf.labs.agents.createOutbound({
  name: "Benefits verification",
  outboundCallMode: {
    enabled: true,
    maxDurationSeconds: 180,
    maxKeypresses: 12,
  },
});
```

```python
sf.labs.agents.create_outbound({
    "name": "Benefits verification",
    "outbound_call_mode": {
        "enabled": True,
        "max_duration_seconds": 180,
        "max_keypresses": 12,
    },
})
```

The normal mission remains active until the runtime detects an IVR. A capable adapter can then execute bounded DTMF navigation, retain state, detect a human, and resume the mission. Transition metadata can explain when navigation started, ended, or stopped for safety.

| Limit | Default | Allowed |
| --- | ---: | ---: |
| IVR duration | 180 seconds | 30–900 |
| Keypresses | 12 | 1–64 |
| Repeated menu | 3 | 1–10 |
| No progress | 30 seconds | 5–120 |

Supafone-managed, Twilio, Telnyx, Plivo, SignalWire, and SIP/BYOC share one public contract. Readiness never comes from a provider name: adapters must positively report required capabilities, and unknown or unsupported capability states fail closed.
