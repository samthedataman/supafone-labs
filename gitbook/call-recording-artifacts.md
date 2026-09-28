# Call Recordings and Artifacts

## Enable native recording explicitly

Native S2S calls record only when `recording` is enabled. A boolean enables or
disables audio capture; an object also requests post-call transcription:

```ts
await supafone.labs.agents.update("northline-intake", {
  recording: { enabled: true, transcribe: true },
});
```

```python
supafone.labs.agents.update(
    "northline-intake",
    recording={"enabled": True, "transcribe": True},
)
```

The native relay records caller audio and agent audio at the transport boundary
and archives the resulting artifact. Output timing is estimated on the server;
it is not proof of what a remote endpoint heard. Optional post-call transcription needs
both recorded audio and the server's configured Deepgram connection. Hydra
has no live transcript stream; this option does not supply live transcript
evidence to the Manager or Supervisor.

Ultravox keeps its existing provider recording and archive path. Provider
transcripts, recorded audio and post-call transcription are distinct artifacts;
a transcript is not proof that audio was retained. Check the completed call's
available artifacts instead of inferring success from requested settings.

## Legacy policy metadata

Older SDK types include recording consent, PII and retention fields. They do
not establish native runtime enforcement. In particular, `recording.retention_days`
is rejected with HTTP 422 until a retention service enforces it; configure
external lifecycle policy separately. The active native controls documented
here are `recording.enabled` and `recording.transcribe`. Do not present a
requested announcement or redaction flag as evidence that it ran.

## Artifact APIs

The SDK exposes account-owned call artifacts under the hosted-agent namespace:

```ts
const calls = await supafone.labs.calls.list({ agentKey: "northline-intake" });
const call = await supafone.labs.calls.get("call_123");
const recordings = await supafone.labs.recordings.list({ callId: "call_123" });
const transcripts = await supafone.labs.transcripts.list({ agentKey: "northline-intake" });

// Signed, short-lived URLs when the recording is available.
console.log(call.call.recording_url, call.call.recording_download_url);

// Explicit deletion operations on an account-owned call.
await supafone.labs.recordings.delete("call_123", { reason: "retention request" });
await supafone.labs.calls.delete("call_123");
```

Recording deletion and call deletion are separate operations. A carrier may
retain its own copy; deleting Supafone's artifact reference does not prove
that every external provider deleted its audio.

Call lifecycle, transcript, recording and Supervisor activity can also be
queried from the activity ledger:

```ts
const supervision = await supafone.labs.activity.list({
  eventType: "watcher.whispered",
  resourceId: "call_123",
});
const plans = await supafone.labs.plans.list();
```

## Shared post-call processing

Browser and phone completion share the enrichment path. Artifacts,
classification, campaign outcomes and call-memory upserts may refresh as late
provider evidence arrives. Notification dispatch uses a durable once-only
claim, with no automatic replay after an ambiguous interrupted dispatch.
Available transcripts feed downstream processing; absent evidence is not
replaced with invented transcript-grounded scores.

See [Shared runtime, Manager and teams](shared-agent-runtime.md) for the full
runtime matrix, Manager limits and model-handoff behavior.
