# Live language and voice routing

## Native S2S language handoff

Native OpenAI, Gemini, Grok and Hydra sessions can use `runtime_routing` with
explicit `allowed_models` and `allowed_languages`. A caller-requested language
switch starts a new allowed model/voice session through the native broker,
keeps the server stage, facts and receipts, and consumes the configured handoff
budget. It does not resume a provider's hidden session state. Hydra is
English-only; another approved model is needed for a Spanish handoff.

See [Shared runtime, Manager and teams](shared-agent-runtime.md#native-model-handoff)
for the configuration. These native provider voices do not use the external-TTS
profile routing described below.

## Ultravox external-TTS profiles


Hosted Agent Factory agents can opt into same-call routing across two to four
approved languages. Each language can use a distinct compatible voice.
Existing agents keep their current fixed-language behavior unless
`languageVoiceRouting` is explicitly enabled.

Native providers use their own model voices. Their separate broker policy can
replace a speaking session; the Ultravox profile settings below are not that
native session-handoff contract.

```ts
const agent = await supafone.labs.agents.createInbound({
  name: "Puerto Rico intake",
  greeting: "Thank you for calling Northline Health. How can I help?",
  languageVoiceRouting: true,
  routingLanguages: ["es-PR", "en-US", "vi-VN"],
});
```

The first language owns the greeting and initial voice. For a non-English
primary language, Supafone translates the supplied or generated greeting
during provisioning and preserves template tokens, names, URLs, and phone
numbers. A translation failure rejects provisioning instead of saving a
mismatched greeting.

When the caller clearly requests or speaks another configured language, the
same call continues with the matching voice. The current stage, tools,
captured facts, campaign context, and prior tool results remain available.
Routing is never based on accent alone.

The same public fields work through REST, Python, TypeScript, and the hosted
agent creation tools in MCP:

| Field | Meaning |
| --- | --- |
| `languageVoiceRouting` / `language_voice_routing` | Explicit opt-in; default `false` |
| `routingLanguages` / `routing_languages` | Two to four ordered locales |
| `languageProfiles` / `language_profiles` | Optional per-language live-catalog voice selections |

The hosted path supports managed Ultravox inbound PSTN, outbound PSTN and
campaign calls, and browser WebRTC. Only the preference contract is public;
the routing policy and call controls remain in Supafone's hosted backend.
Automatic translation applies to the inbound/browser agent greeting; reviewed
outbound and campaign opening copy remains authoritative.

See the
[complete GitBook guide](https://github.com/samthedataman/supafone-labs/blob/main/gitbook/live-language-voice-routing.md)
for full REST, Python, TypeScript, MCP, PSTN, campaign, WebRTC, and
troubleshooting examples.
