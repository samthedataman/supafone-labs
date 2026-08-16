# Live Language and Voice Routing

Agent Factory can keep one call active while a caller moves between two to
four approved languages. Each language can use its own compatible voice. The
feature is opt-in and disabled for every existing agent unless
`languageVoiceRouting` is explicitly `true`.

## What changes and what stays the same

| Configuration | Runtime behavior |
| --- | --- |
| Routing field omitted or `false` | Historical fixed-language and fixed-voice behavior |
| `languageVoiceRouting: true` | English and Spanish profiles are selected automatically |
| Routing plus `routingLanguages` | Two to four ordered languages; the first owns the greeting |
| Routing plus `languageProfiles` | The same routing behavior with developer-selected live-catalog voices |

When a switch is accepted, the active language and matching voice change on
the same call. The agent keeps its current stage, prompt, tools, captured
facts, campaign context, and prior tool results. The caller does not restart
intake or repeat information.

This is language routing, not accent classification. A name, nationality,
accent, background speaker, or isolated borrowed word is not enough to change
the active language.

## Greeting behavior

The first configured language is the primary language:

- it controls the initial language hint and voice;
- it controls the inbound and browser-call greeting; and
- when it is not English, Supafone automatically translates the supplied or
  generated greeting during provisioning.

Translation preserves template tokens, business names, phone numbers, and
URLs. Agent creation returns a clear error rather than silently saving an
English greeting for a non-English primary language when translation is
unavailable. Switching later in the call does not replay the greeting.

Outbound calls still follow outbound etiquette: the recipient answers first,
the primary language and voice are active, and the reviewed campaign or
outbound introduction remains authoritative. Automatic greeting translation
does not overwrite campaign-specific opening copy, and an inbound greeting is
never played into a ringing line. Localize custom outbound opening copy in the
campaign or outbound-agent configuration.

## TypeScript

Use the automatic voice-selection path first:

```ts
const agent = await supafone.labs.agents.createInbound({
  agentKey: "puerto-rico-intake",
  name: "Puerto Rico intake",
  businessName: "Northline Health",
  greeting: "Thank you for calling Northline Health. How can I help?",
  languageVoiceRouting: true,
  routingLanguages: ["es-PR", "en-US", "vi-VN"],
});

console.log(agent.language_voice_routing?.profiles);
console.log(agent.language_voice_routing?.greeting_translation);
```

The response shows the resolved public profile for every language. Voice
selection comes from the account's current configured catalog.

For explicit control, select catalog voices and pass them as profiles:

```ts
const agent = await supafone.labs.agents.createInbound({
  agentKey: "curated-intake",
  name: "Curated intake",
  languageVoiceRouting: true,
  languageProfiles: [
    {
      language: "en-US",
      voice: {
        provider: "cartesia",
        voiceId: "<current-catalog-voice-id>",
        model: "sonic-3.5",
      },
    },
    {
      language: "es-MX",
      voice: {
        provider: "cartesia",
        voiceId: "<current-catalog-voice-id>",
        model: "sonic-3.5",
      },
    },
  ],
});
```

## Python

```python
agent = supafone.labs.agents.create_inbound({
    "agentKey": "puerto-rico-intake",
    "name": "Puerto Rico intake",
    "businessName": "Northline Health",
    "greeting": "Thank you for calling Northline Health. How can I help?",
    "languageVoiceRouting": True,
    "routingLanguages": ["es-PR", "en-US", "vi-VN"],
})

print(agent["language_voice_routing"]["profiles"])
```

Python accepts camelCase for copy-and-paste parity and snake_case for native
Python style.

## REST

```bash
curl https://api.supafone.ai/api/v1/labs/agents \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Puerto Rico intake",
    "business_name": "Northline Health",
    "greeting": "Thank you for calling Northline Health. How can I help?",
    "language_voice_routing": true,
    "routing_languages": ["es-PR", "en-US"]
  }'
```

## MCP

The four hosted creation tools accept the same public fields:

- `create_inbound_agent`
- `create_outbound_agent`
- `create_inbound_agent_with_number`
- `create_outbound_agent_with_number`

Example request to an MCP client:

> Create an inbound agent with live language and voice routing. Start in Puerto
> Rican Spanish, also support English and Vietnamese, and choose compatible
> configured voices automatically.

The MCP server submits only the public preferences. It does not contain the
hosted detection or call-transition implementation.

## PSTN, campaigns, and WebRTC

One Agent Factory configuration is reused across the managed call paths:

| Call path | Supported behavior |
| --- | --- |
| Inbound PSTN | Primary translated greeting, then same-call routing |
| Outbound PSTN | Recipient speaks first; primary language/voice plus the reviewed outbound introduction, then same-call routing |
| Outbound campaign | Campaign stage, recipient context, and tools survive a route |
| Browser WebRTC | Same primary greeting and routing contract without Twilio |

The current hosted routing adapter is managed Ultravox. The provider-neutral
Voice Watcher framework supports other voice stacks, but this Agent Factory
provisioning flag does not claim live voice-switch control for arbitrary BYOK
agent runtimes.

## Voice selection rules

Automatic selection prefers a voice native to the requested language and then
falls back to a voice whose configured model supports that language in the
managed runtime. Every profile must resolve to a distinct, connected,
runtime-compatible voice.

Use the [Dynamic Voice Catalog](voice-catalog-and-selection.md) to inspect
language compatibility. Agent creation returns `422` for unsupported
languages, stale voice IDs, disconnected providers, incompatible voices, or a
duplicate voice assigned to multiple profiles.

## Compatibility and safety

- Existing agents are unchanged because the opt-in defaults to `false`.
- Manual product builders are unchanged; this contract belongs to Agent
  Factory agents only.
- The primary language is deterministic: first profile, unless an explicit
  `preferredLanguage` selects and promotes one of the profiles.
- Only the boolean, ordered language list, and optional voice preferences are
  public. Detection policy, call controls, and security checks remain in the
  hosted Supafone runtime.
- Supafone can disable the hosted feature operationally without changing
  existing agent configuration.

## Troubleshooting

| Response | Meaning | Action |
| --- | --- | --- |
| `422` unsupported language | The locale is outside the managed runtime intersection | Query voice capabilities and choose a supported language |
| `422` voice not in catalog | The ID is stale or belongs to an unconnected provider | Refresh `GET /voices` and select a current configured voice |
| `422` incompatible or duplicate voice | The profile cannot run that language or reuses another profile's voice | Choose a distinct compatible voice |
| `503` routing disabled | The hosted safety switch is off | Keep fixed-language mode or retry after service restoration |
| `503` greeting translation unavailable | A non-English primary greeting could not be safely translated | Retry provisioning; Supafone does not save the mismatched greeting |

Next: [Agent Factory](agent-factory.md), [Hosted Agents API](hosted-agents-api.md),
[Browser WebRTC Calls](browser-webrtc-calls.md), and
[Outbound Call Campaigns](outbound-call-campaigns.md).
