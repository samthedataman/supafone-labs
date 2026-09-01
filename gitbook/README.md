<p align="center">
  <img src=".gitbook/assets/supafone-logo.png" alt="Supafone" width="104" height="104" />
</p>

# Supafone Labs

**Production infrastructure for voice agents that need to work after the demo.**

[Python SDK](https://pypi.org/project/supafone-labs/) ·
[TypeScript SDK](https://www.npmjs.com/package/supafone-labs) ·
[GitHub](https://github.com/samthedataman/supafone-labs) ·
[Developer console](https://labs.supafone.ai) ·
[API reference](https://api.labs.supafone.ai/docs)

## The so what

**A normal voice framework helps an agent speak. Supafone helps developers
build, test, operate, supervise, and improve the entire voice product.**

Use one Supafone API key for the production systems that otherwise become
separate integrations: phone and WebRTC delivery, managed voices, grounded
knowledge, verified tools, email, live supervision, recordings, transcripts,
QA, and post-call evidence. Start with Supafone-managed infrastructure, or
keep the realtime model, carrier, and speech providers you already use.

[Follow the 10-minute quickstart](quickstart.md) ·
[Create an API key](https://labs.supafone.ai/console.html?mode=register) ·
[Open the workspace](https://labs.supafone.ai/builder.html) ·
[Review framework coverage](framework-support.md)

## What changes for the developer

| Production work you would otherwise build | What Supafone provides |
| --- | --- |
| Reconcile telephony, WebRTC, speech, knowledge, tools, email, supervision, and QA | **One integration** and one account model across the call lifecycle |
| Replace a working agent to gain observability or guardrails | **Keep your existing stack** and attach Supafone Supervisor through the supported provider adapter |
| Ask the speaking model to notice its own mistakes | **Independent supervision** that stays off the audio hot path and emits a bounded instruction only when evidence is strong |
| Trust spoken claims about bookings, transfers, sends, or CRM writes | **Verified actions** that separate tool truth from model language |
| Build carrier search, purchasing, assignment, and release workflows | **Managed phone provisioning** without requiring a separate Twilio control plane |
| Buy a number before hearing the agent | **Browser WebRTC testing first**, then real PSTN testing when the agent is ready |
| Integrate every speech provider independently | **One searchable catalog of 1,600+ normalized voices** with provider, language, style, compatibility, and preview metadata |
| Assemble crawling, chunking, embeddings, retrieval, and reranking | **Private grounded knowledge** from approved websites and documents |
| Put intake, qualification, scheduling, IVR, language changes, and campaigns into one prompt | **Reusable multi-stage behavior** with bounded IVR navigation, language-aware voice profiles, handoffs, and campaigns as code |
| Reconcile recordings, transcripts, provider logs, and QA results | **Complete call evidence** linked to the agent, tool outcomes, and Supervisor decisions |
| Commit to one programming surface | **Python, TypeScript, REST, WebSocket, and MCP** over the same hosted contracts |
| Rebuild the surrounding product for every customer | **Faster delivery** focused on the agent's objective, business rules, and customer experience |

## Voices without five separate integrations

The managed catalog currently normalizes more than 1,600 voices across
Cartesia Sonic, ElevenLabs, Inworld TTS-2, Deepgram Aura, and Ultravox's
speech-native managed voices. Search and preview by provider, language, gender,
and style, then deploy a compatible managed voice without adding that provider's
API key. BYOK remains available for teams that need a specific provider account
or private voice.

## Cost comparison

Supafone Cloud is **$0.10 per connected minute** for the standard managed call
stack, including managed models, compatible voices, telephony, transcripts,
Supafone Supervisor, and QA. The account receives five managed-runtime minutes;
a 400-minute reload is $40. The allowance is shared across its keys, agents,
WebRTC sessions, PSTN calls, SDKs, CLI, and MCP. There is no seat fee.

Managed calls atomically reserve available seconds before provider startup, so
concurrent calls cannot spend the same balance. Settlement refunds unused held
time. When no call can be reserved, the API returns a structured HTTP 402 and a
server-authored Stripe Checkout path. See
[Pricing, Credits, and Checkout](pricing-and-credits.md#structured-402-payment-flow).

That $0.10 pays for the production path, not only the SDK call that starts it.
Supafone operates the carrier connection, compatible model and voice runtime,
artifact pipeline, Supervisor inference, and QA record under one meter. It also
removes the engineering and operational overhead of securing several vendor
credentials, reconciling their usage records, and rebuilding the same control
plane for each agent. Teams that already have better provider economics can use
BYOK and keep Supafone as the common runtime and evidence layer.

Competitor headline rates often meter only one layer of the stack. This table
keeps the published rate and the separately billed pieces visible:

| Platform | Published connected-minute rate | What remains separate |
| --- | ---: | --- |
| **Supafone Cloud** | **$0.10** | Standard managed stack is bundled; optional BYOK usage stays with that provider |
| [Vapi](https://vapi.ai/pricing) | $0.05 platform fee | Model, STT, TTS, and carrier usage |
| [Retell](https://www.retellai.com/pricing) | $0.07-$0.31; published sample $0.11 | Final rate varies by voice, model, telephony, knowledge, guardrails, and QA choices |
| [Deepgram Voice Agent](https://deepgram.com/pricing) | $0.075 standard; $0.065 with BYO TTS | External carrier and any BYO service usage |
| [ElevenAgents](https://elevenlabs.io/pricing/agents) | $0.08 additional-call rate | LLM and telephony usage |
| [Bland](https://www.bland.ai/pricing) | $0.14 on Start | Carrier usage; lower published minute rates require monthly platform plans |

At 10,000 connected minutes, Supafone's standard managed stack is $1,000. The
same published-volume subtotal is $500 for Vapi before model, speech, and
carrier usage; $750 for Deepgram before carrier; $800 for ElevenAgents before
LLM and telephony; and $1,400 for Bland Start before carrier. The point is not
that every workload has the same provider mix. It is that Supafone's headline
rate describes the standard production stack, while many headline rates are a
base layer that still needs several services and integrations.

Rates checked August 31, 2026. Vendor prices and inclusions change; follow the
linked pricing pages before making a purchasing decision.

## Why we built it

A voice demo can be assembled quickly. A dependable voice product cannot. The
production agent is split across a realtime model, telephony, TTS, STT, tools,
retrieval, state, recordings, compliance, monitoring, and post-call workflows.
Every vendor exposes a different event format, and the speaking model is still
expected to notice and correct its own mistakes while talking.

Supafone Labs was built around the failures that appear at those boundaries:

| Production problem | Supafone innovation | What changes for the developer |
| --- | --- | --- |
| The speaking agent must supervise itself | **Supafone Supervisor** runs beside the call and issues one bounded directive only when evidence is strong | Add supervision without replacing the agent or extending the audio hot path |
| Every voice platform has different events and controls | **Canonical runtime plus 14 audited adapters** normalize call events and compile guidance into the control each platform actually supports | Keep the current provider and reuse the same supervision, QA, and telemetry |
| Prompts make operational claims that tools never confirmed | **Truth state and guardrail policies** track verified bookings, transfers, deliveries, consent, and failures separately from model language | Prevent the agent from claiming an action succeeded before a tool proves it |
| Every new agent starts as another prompt-engineering project | **Agent Factory** turns a job description into editable stages, tools, routing, numbers, voices, and artifacts | Provision complete inbound, outbound, browser, and campaign agents through one API |
| Testing is manual role-play | **Adversarial QA and SSR grading** generate scenarios from the agent objective and compare supervised with unsupervised behavior | Measure regressions and supervision lift before deployment |
| Calls disappear into provider dashboards | **Durable activity APIs** retain agents, plans, calls, recordings, transcripts, supervision events, and post-call outcomes | Build one operational console instead of reconciling vendor logs |
| Multilingual calls lose context or use the wrong voice | **Language-aware transcription and opt-in language/voice profiles** preserve the active workflow while the language changes | Configure multilingual behavior without rewriting the agent graph |
| Phone, WebRTC, SMS, campaigns, and signing become separate systems | **One SDK and one account model** connect managed delivery, messaging, campaigns, artifacts, and writebacks | Stop rebuilding the surrounding product for every customer |

## The architecture

```text
Caller -> speaking agent -> tools and business systems
             |                         |
             +---- call events --------+
                          |
                          v
               canonical call state
                    |          |
                    v          v
              live supervision   call artifacts
                    |
          confidence + policy gate
                    |
              provider adapter
                    |
          silent bounded guidance
                    |
                    +------> speaking agent
```

The call never waits for the Supervisor. If supervision is unavailable, late, or
uncertain, the gate emits no directive and the original agent continues.

## Two ways to use the package

### Supervise an agent you already run

```python
import supafone_labs

supervisor = supafone_labs.supercharge(my_agent)
result = await supervisor.observe(provider_event)
```

The package auto-detects supported agents when possible, normalizes their
events, and returns the provider-appropriate action. Start with
[Supafone Supervisor](supafone-supervisor.md), then check the
[framework coverage matrix](framework-support.md).

### Provision the complete agent

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_TOKEN! });

const agent = await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake",
  name: "Northline intake",
  description: "Understand the request and book the right next step.",
  number: { search: { areaCode: "415" } },
});
```

Agent Factory adds the plan, number, voice, stages, tools, call artifacts, and
live supervision. Developers can inspect and edit the generated plan before creation.

## Framework coverage

The release gate covers fourteen runtime integrations, not a marketing-only
logo list:

- **Native control:** Supafone Agent Factory, Ultravox, Vapi, OpenAI Realtime,
  Grok Voice Agent, Gemini Live, ElevenLabs Agents, Deepgram Voice Agent, and
  Inworld Realtime.
- **Context owned by the developer:** Retell custom LLM, LiveKit Agents, and
  Pipecat.
- **Observation or explicit hook:** Bland and Cartesia Line.
- **Extension path:** `GenericWebhookAdapter` for proprietary systems.

Integration depth is different for each provider. The
[complete framework matrix](framework-support.md) shows the exact control,
acceptance criterion, and managed-delivery status for every runtime.

## Package surfaces

| Surface | Use it for |
| --- | --- |
| Python | Local runtime, adapters, replay, supervision, STT/TTS components, and backend automation |
| TypeScript | Node, React, browser, Agent Factory, campaigns, activity, and product integrations |
| REST and WebSocket | Hosted agents, realtime services, events, recordings, transcripts, and custom clients |
| MCP | Agent creation, calls, QA, logs, and operational workflows from AI development tools |

## Start here

1. Read [the production problems](production-voice-ai-challenges.md).
2. Follow the [quickstart](quickstart.md).
3. Understand [Supafone Supervisor](supafone-supervisor.md).
4. Review [all supported frameworks](framework-support.md).
5. Install the [Python or TypeScript SDK](sdk-installation.md).
6. Choose [managed delivery or BYOK](byok-providers.md).
7. Run the [voice-agent QA workflow](voice-qa-landscape.md).

Supafone Labs exists so developers can define the caller experience, tools,
and safety policy while one framework handles the infrastructure around them.
