# Outbound IVR call mode

Supafone Labs `0.5.0` adds an opt-in, provider-neutral contract that lets an outbound agent temporarily navigate a phone tree and then resume its original mission when a human answers.

The SDK stores the contract under `metadata.outbound_call_mode` for hosted agents and `settings.outbound_call_mode` for campaigns. Omitting it preserves existing behavior; `{ enabled: false }` serializes only the version and disabled flag.

## Python

```python
from supafone_labs import Supafone, outbound_call_mode_readiness

sf = Supafone(api_key="sf_live_...")
agent = sf.labs.agents.create_outbound({
    "name": "Benefits verification",
    "outbound_call_mode": {
        "enabled": True,
        "max_duration_seconds": 180,
        "max_keypresses": 12,
    },
})

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
```

## TypeScript

```ts
import Supafone, { outboundCallModeReadiness } from "supafone-labs";

const sf = new Supafone({ apiKey: "sf_live_..." });
await sf.labs.agents.createOutbound({
  name: "Benefits verification",
  outboundCallMode: {
    enabled: true,
    maxDurationSeconds: 180,
    maxKeypresses: 12,
  },
});

const readiness = outboundCallModeReadiness(
  { enabled: true },
  {
    provider: "telnyx",
    dtmf: true,
    statePersistence: true,
    humanDetection: true,
    observability: true,
  },
);
```

## Public controls

| Control | Default | Bounds |
| --- | ---: | ---: |
| Maximum IVR duration | 180 seconds | 30–900 |
| Maximum keypresses | 12 | 1–64 |
| Repeated-menu limit | 3 | 1–10 |
| No-progress timeout | 30 seconds | 5–120 |

Auto-detection, DTMF use, human detection/resume, and transition observability default on only after the overall mode is explicitly enabled.

## Provider readiness

The same contract covers Supafone-managed, Twilio, Telnyx, Plivo, SignalWire, and SIP/BYOC transports. A provider name never implies execution support. The active adapter must positively report DTMF, state persistence, human detection, and observability capabilities; missing or false capabilities fail closed.

The public SDK defines configuration, serialization, readiness checks, and lifecycle calls. Phone-tree detection, prompts, runtime models, and carrier execution remain private managed-runtime responsibilities.
