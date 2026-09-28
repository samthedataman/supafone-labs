# Shared Agent Factory runtime

Agent Factory separates the **call workflow** from the **speaking model**.
Ultravox, OpenAI, Gemini, Grok and Smallest AI Hydra use the same hosted stage
plan, server tools, Manager and Supervisor. Provider and carrier capabilities
still determine how those controls reach a live call.

This page describes the implemented API contract. A catalog entry or configured
key is not evidence of a successful live call. Verify the deployed API and the
selected model/carrier before marking a route ready in your application.

## Responsibilities

| Component | Job | Authority |
| --- | --- | --- |
| Agent Factory | Create an agent, its reviewed plan, tools and team | Stores configuration |
| Call runtime | Track stage, specialist, saved facts, tool receipts and budgets | Validates and commits state changes |
| Manager | Propose the next permitted stage or specialist; consult specialists | Proposals must pass runtime checks |
| Specialist | Answer a bounded question using its configured role | Returns advice; does not execute business tools |
| Supervisor | Observe available evidence and suggest a correction | Advice cannot create facts, permissions or successful outcomes |
| Speaking model | Talk with the caller and request configured tools | One active provider owns caller-facing audio |
| Phone/browser transport | Carry audio, recording and supported call controls | Enforces call and account ownership |

A specialist consultation is a separate reasoning task. It is not another
simultaneously speaking S2S session. A model handoff creates a replacement
speaking session through the native session broker.

## Call stages that survive a provider change

The hosted planner produces **3–8 stages**, or you can supply a reviewed
`call_stages` array. The default template remains available when hosted planning
cannot complete. Updating an agent's `realtime` selection preserves its plan.
An active call uses its frozen plan and team; edits apply to later calls.

Each stage can contain:

- `key`, `name`, `goal` and `instructions`;
- `next_stages`: legal outgoing edges, with `[]` marking a terminal stage;
- `tools`: allowed business tool names; an explicit `[]` disables business tools;
- `requirements.required_fields`: configured fields saved by a successful `save_lead`;
- `requirements.successful_tools`: successful tool receipts from the current stage;
- optional `role` and `specialist_id`; `temperature` is mapped on Ultravox only.

`exit_criteria` remains conversational guidance. Supafone does not pretend that
an arbitrary sentence is an executable condition. Machine checks come from the
structured `requirements` object. Saved facts identify caller-provided values
that a server handler saved; they are not independent verification of identity
or truth.

The runtime rejects skipped stages, invalid branches, unsatisfied requirements,
and tools outside the active stage or specialist's permissions. Legacy stages
without a tool list retain their configured tools and advance along their
existing sequential edges. Call controls and enabled coaching/management tools
have separate capability checks; transfer still requires stage permission.

Gemini declares the approved plan's tool union when a session opens, then the
server checks active permissions on each invocation. OpenAI and Grok can update
their session instructions. Hydra receives approved stage instructions through
tool results because its initial persona is immutable. Native adapters do not
currently apply per-stage temperature; the Ultravox path maps it to its
provider request.

## Configure a team, Manager and execution gates

```ts
const agent = await supafone.labs.agents.createInbound({
  agentKey: "booking-team",
  name: "Booking team",
  realtime: { provider: "openai", model: "gpt-realtime-2.1", voice: "marin" },
  captureFields: ["name", "email"],
  timezone: "America/New_York",
  timeAwareness: true,
  tools: { scheduling: true, firmKnowledge: true },
  supervisor: true,
  manager: {
    enabled: true,
    reasoning: "managed",
    model: "supafone-manager",
    maxTasks: 12,
    maxParallel: 2,
    timeoutSeconds: 6,
  },
  agentTeam: {
    enabled: true,
    fallbackMemberId: "scheduler",
    members: [{
      id: "scheduler",
      label: "Scheduling specialist",
      instructions: "Explain booking options using the available evidence. Never invent availability.",
      stageKeys: ["book"],
      tools: ["check_availability", "book_appointment"],
    }],
  },
  callStages: [
    { key: "capture", name: "Capture", goal: "Confirm and save the caller's name.",
      tools: ["save_lead"], requirements: { requiredFields: ["name"] }, nextStages: ["book"] },
    { key: "book", name: "Book", goal: "Offer a real slot and book only after the caller agrees.",
      tools: ["check_availability", "book_appointment"],
      requirements: { successfulTools: ["book_appointment"] }, nextStages: ["confirm"] },
    { key: "confirm", name: "Confirm", goal: "Recap the successful booking and say goodbye.",
      tools: [], nextStages: [] },
  ],
});
```

A connected calendar is still required. A failed booking never satisfies the
`book_appointment` requirement. Stage and specialist decisions use revision
checks so late reasoning cannot overwrite newer facts or actions.

Python accepts the same fields with snake_case: `capture_fields`, `agent_team`,
`stage_keys`, `call_stages`, `required_fields`, `successful_tools`, `max_tasks`,
`max_parallel` and `timeout_seconds`. Both SDKs also preserve explicit empty
stage tool/edge arrays on creation and patch.

The Manager is opt-in. Its defaults are 12 reasoning tasks per call, two in
parallel and a six-second task timeout. Failed and timed-out tasks consume the
budget. Allowed configuration ranges are 1–30 tasks, 1–4 parallel tasks and
1–15 seconds. `reasoning: "supervisor"` reuses the existing encrypted Supervisor
profile; otherwise managed server credentials are used. There is no separate
client-visible Manager API key.

## Tool receipts and recovery

Before a business tool runs, the server claims its invocation ID in durable
call state. Repeated IDs return the completed result or a pending/conflict
status. A timeout or crash after submission does not authorize replaying a
booking, message or other write. This avoids blind duplicate submissions; it
is not a claim of exactly-once effects in an external system without that
system's own idempotency support.

Successful receipts record the actual handler outcome and execution stage.
Manager or Supervisor text cannot create those receipts. Completed failed
attempts are retained separately so recovery cannot mistake them for success.

## Native model handoff

Normal `engine.apply()` or `agents.update({realtime: ...})` changes the saved
selection for **future calls**. Mid-call native switching is a separate opt-in:

```ts
await supafone.labs.agents.update("booking-team", {
  runtimeRouting: {
    enabled: true,
    allowedModels: [
      { provider: "openai", model: "gpt-realtime-2.1", voice: "marin" },
      { provider: "xai", model: "grok-voice-latest", voice: "eve" },
    ],
    maxHandoffs: 1,
    recoverOnDisconnect: false,
    allowedLanguages: ["en"],
  },
});
```

Targets are restricted to configured provider/model/voice selections.
`max_handoffs` accepts 1–3. The broker preserves server state, receipts and a
bounded conversation history, cancels the old output and keeps one speaking
provider active. Audio is converted to the established transport format.

A handoff opens a **new provider session**; it is not seamless resumption of a
vendor's hidden conversation state. Optional disconnect recovery attempts at
most one replacement and remains subject to the handoff budget and available
credentials. `allowed_languages` is an explicit permission list, not proof of
language quality; Hydra only accepts English. The `route_spoken_language`
control requires an explicit caller request and a configured language/target.
A request for Spanish on Hydra needs another approved speaking model. Language
routing uses the same handoff budget and preserves the server workflow; it
opens a provider-native voice session and does not use Ultravox's external-TTS
profile router. Ultravox-to-native or native-to-Ultravox live session handoff
is not implemented.

## Recording, transcripts and finalization

Native calls record only when configured with `recording: true` or
`recording: {enabled: true, transcribe: true}`. Supafone captures the caller and
agent audio at the transport boundary and archives the result. Output timing
is a server estimate; this is not proof that a remote caller heard a sample.
Post-call transcription additionally requires the server's Deepgram connection
and a recording; it does not add a live transcript stream to Hydra.

Browser and phone completion use the same enrichment path. Artifact fetches,
classification, campaign outcome mapping and call-memory upserts may refresh
when late provider evidence arrives. Notification dispatch uses a durable
once-only claim; an ambiguous interrupted dispatch is not automatically
replayed. This does not claim exactly-once delivery by an email provider.
Unavailable evidence remains unavailable; no score should be presented as
transcript-grounded without transcript evidence.

See [Call recordings and artifacts](https://labs.supafone.ai/docs/call-recording-artifacts/)
for artifact access and the distinction between active controls and legacy
recording-policy metadata.

## Capability matrix

| Feature | Ultravox hosted path | Native OpenAI / Gemini / Grok / Hydra |
| --- | --- | --- |
| Generated/custom stages, execution gates | Shared runtime | Shared runtime |
| Per-stage temperature | Mapped to provider request | Not applied by native adapters |
| Manager and specialist consultations | Hosted HTTP tools | Native tool results |
| Supervisor coaching | Hosted guidance tool | Native guidance tool; Hydra context is model-reported |
| Knowledge, capture, calendar, email/SMS, custom hooks | Configured shared handlers | Configured shared handlers |
| Public browser widget | Hosted transport | Native browser relay |
| Recording | Existing provider recording/archive path | Opt-in relay recording |
| Transcripts | Provider transcript | Provider transcript except Hydra; optional recording-based post-call transcription |
| End call | Existing hosted/carrier behavior | Browser and configured phone transports |
| Media pause | Provider-dependent | Short pause of Supafone audio; not carrier hold/music |
| DTMF | Enabled Ultravox built-in | Carrier API or audio tones; remote IVR recognition is not guaranteed |
| Human transfer | Existing Twilio path plus configured Telnyx, Plivo or bound LiveKit SIP controls | Configured Twilio, Telnyx, Plivo or LiveKit SIP cold transfer; acceptance does not prove answered |
| Native voicemail detection/message tool | Existing enabled Ultravox built-in | Not implemented |
| Live native-provider handoff | Not in the native broker | Explicit allowed targets; replacement session |
| External TTS / supported brand voices | Existing compatible external-voice mappings | Native provider voices; no arbitrary external TTS replacement |
| Language/voice routing | Existing opt-in external-TTS profiles | Explicit caller-requested language handoff to an allowed native model/voice; replacement session |

Phone controls also require the chosen carrier's credentials and live call
identity. A shared workflow contract does not mean every carrier action,
voice-cloning feature or provider control behaves identically.
