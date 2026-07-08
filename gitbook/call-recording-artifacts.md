# Call Recording and Artifacts

Call recording is an explicit agent policy. Do not silently enable it without a
user/admin choice and an appropriate consent path.

## Agent Creation Policy

```ts
await supafone.labs.agents.createInbound({
  agentKey: "northline-intake",
  name: "Northline intake",
  recording: {
    enabled: true,
    recordAudio: true,
    consentRequired: true,
    announcement: "This call may be recorded for quality and training.",
    retentionDays: 30,
    redactPii: true
  },
  transcription: {
    enabled: true,
    provider: "supafone_managed",
    language: "multi",
    diarization: true,
    timestamps: true,
    redactPii: true
  },
  artifacts: {
    recordings: true,
    transcripts: true,
    summaries: true,
    qaReports: true,
    logs: true,
    retentionDays: 30
  }
});
```

Python uses the same payload shape and serializes it to snake_case for the API.

## Artifact APIs

The SDK exposes call artifacts under the hosted-agent namespace:

```ts
const calls = await supafone.labs.calls.list({ agentKey: "northline-intake" });
const recordings = await supafone.labs.recordings.list({ callId: "call_123" });
const transcripts = await supafone.labs.transcripts.list({ agentKey: "northline-intake" });

await supafone.labs.recordings.delete("rec_123", { reason: "retention request" });
```

Builder UI should expose:

- record calls on/off,
- transcribe calls on/off,
- retention days,
- consent announcement,
- recent calls,
- recordings,
- transcripts,
- delete recording where backend policy permits.

## Compliance Notes

- Laws vary by jurisdiction. Product defaults should support consent prompts,
  retention limits, and PII redaction.
- For regulated customers, prefer explicit admin policy and account-level
  defaults over silently inferred recording.
- BYOK telephony may store recordings at the carrier too. The UI should make it
  clear whether artifacts are Supafone-managed, provider-managed, or both.
