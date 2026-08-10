# Browser WebRTC Calls

Supafone Labs `0.4.10` exposes browser voice sessions directly through the
Python and TypeScript SDKs. A WebRTC session connects a browser microphone to
an owned Supafone voice agent without buying a phone number or creating a PSTN
call.

## WebRTC versus phone calls

| Path | Transport | Phone number required | Typical use |
| --- | --- | --- | --- |
| Browser WebRTC | Browser → Ultravox WebRTC → agent | No | In-browser testing, embedded voice intake |
| One-off PSTN | Carrier/Twilio → agent → destination phone | Yes | Call one person immediately |
| Campaign PSTN | Campaign scheduler → carrier → recipients | Yes | Consented outbound sequences at scale |

WebRTC does not route through Twilio. It therefore does not inherit PSTN
transfer behavior, carrier caller ID, or telephone-network recording rules.

## TypeScript

Create the session from a trusted application using the same product-account
authentication used by calls and campaigns:

```ts
import { Supafone } from "supafone-labs";

const sf = new Supafone({
  apiKey: process.env.SUPAFONE_TOKEN!, // sl_live_... or account auth
});

const { agents } = await sf.listVoiceAgents();
const started = await sf.startWebRtcCall({ agentId: String(agents[0].id) });

if (!started.browser_session.available) {
  throw new Error("Browser voice is unavailable for this agent");
}

console.log(started.browser_session.transport); // "ultravox"
console.log(started.browser_session.join_url);
```

`startBrowserCall()` is an alias for browser-oriented codebases.

The current provider adapter is Ultravox:

```ts
import { UltravoxSession } from "ultravox-client";

const call = new UltravoxSession();
await call.joinCall(started.browser_session.join_url!);

// Later, when the user ends the browser call:
await call.leaveCall();
```

The browser will request microphone permission. The application should show a
clear connected/listening state and always provide an end-call control.

## Python

Python creates the same browser-session contract. A common pattern is to call
this from FastAPI and return only `browser_session` to the React client:

```python
from supafone_labs import Supafone

sf = Supafone()  # SUPAFONE_TOKEN=sl_live_...

started = sf.start_webrtc_call(agent_id="agent-123")
browser_session = started["browser_session"]

if not browser_session["available"]:
    raise RuntimeError("Browser voice is unavailable for this agent")

return browser_session
```

CamelCase aliases `startWebRtcCall()` and `startBrowserCall()` remain available
for cross-language code generators.

## Response contract

```json
{
  "version": "1",
  "available": true,
  "provider": "ultravox",
  "transport": "ultravox",
  "join_url": "wss://...",
  "features": {
    "microphone": true,
    "speaker_audio": true,
    "live_transcripts": true
  }
}
```

Clients must switch on `transport`; they should not infer a provider protocol
from the URL. This keeps the SDK contract stable when additional browser
adapters are introduced.

## Security and operational boundaries

- Do not embed a long-lived Supafone account token in a public website. Create
  the session on your server and return only the short-lived browser contract.
- The current hosted browser adapter is Ultravox. Other realtime providers are
  not yet exposed through this SDK method.
- Pure WebRTC sessions cannot perform a native telephone cold/warm transfer.
  Use the Twilio Voice SDK or a PSTN call path when a human phone transfer is
  required.
- The primary greeting, tools, call stages, knowledge, and transcript handling
  come from the selected agent; creating a browser session does not clone or
  modify that agent.
- Browser test sessions are rate-limited by the product API. Production public
  voice widgets should use their provisioned widget/session endpoint rather
  than treating the test-call endpoint as an unlimited public relay.

## Call flow

```text
Trusted backend/control panel
        │ startWebRtcCall(agentId)
        ▼
Supafone product API
        │ short-lived browser session
        ▼
Browser + microphone
        │ WebRTC
        ▼
Ultravox agent runtime
        │
        ├── stages and tools
        ├── knowledge and memory
        └── transcript and post-call artifacts
```
