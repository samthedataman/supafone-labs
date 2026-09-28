# Dynamic Voice Catalog and Selection

Supafone exposes one normalized voice catalog across Ultravox, Cartesia,
ElevenLabs, Inworld, and preview-only Deepgram entries. Developers can discover the voices their account can
actually use, filter them with stable fields, preview them, or ask Supafone to
select one from a plain-language description.

The catalog is live. Supafone pages each connected provider API to exhaustion,
normalizes the results, and caches the account-scoped result for 10 minutes.
Provider additions therefore appear without an SDK release.

## Native realtime model voices

This catalog describes synthesis/TTS voices. Native S2S voices belong to the selected realtime model and are validated by `GET /api/v1/agents/catalog`; they are documented separately in [Native Realtime Agent Factory](realtime-agent-factory.md). Do not mix a Cartesia/ElevenLabs voice ID into a native realtime selection.

## Provider Brands and Logos

Catalog schema version 2 includes stable presentation data for every voice:

- `provider_label`: canonical synthesis-provider display name;
- `provider_logo_url`: browser-ready provider mark when known;
- `provider_brand`: key, name, logo slug/URL, and official website;
- `runtime_provider_brand`: the realtime runtime's brand when it differs from
  the TTS provider;
- `provider_brands`: the distinct synthesis brands represented by the complete
  catalog result.

This keeps provider naming consistent in dashboards built with either SDK. Do
not infer the TTS provider from the runtime: an Ultravox call can render an
ElevenLabs, Cartesia, Inworld, or another provider-backed voice.

The published Python and TypeScript SDKs expose `labs.voices.list` with
provider, language, model, and other catalog filters. Version 0.7.0 also exposes
`listAll` (Python `list_all`) for automatic pagination, plus `capabilities`,
`recommend`, `preview`, and `selection`. `selection(voice)` creates the voice
configuration accepted by managed agent creation. The REST catalog below
exposes the same hosted operations; these helpers do not make external TTS
compatible with every native S2S model.

Unknown providers can remain visible with a text or monogram fallback. Being
listed is not proof of live-call compatibility. Inspect `runtime_selectable`,
`runtime_support_reason`, and the provider's integration capability. Deepgram
entries currently support previews but cannot be selected for managed Ultravox
calls. A custom SDK `TTSProvider` also does not register a hosted call bridge.
See [voice-output choices](voice-output-modes.md).

## The Compatibility Rule

A provider having a voice does not automatically mean that voice can run in
every language on a live Supafone call. Supafone keeps three sets separate:

1. `native_language_codes`: languages or locales advertised for that voice.
2. `model_language_codes`: languages supported by its selected TTS model.
3. `runtime_supported_language_codes`: the intersection of the TTS model and
   Ultravox's spoken-language set.

For a live call, the effective language set is:

```text
provider model languages INTERSECT Ultravox spoken languages
```

Native language is then used for ranking. A cross-lingual model may speak a
different supported language, but a voice native to the requested language is
ranked higher because it generally gives better accent and speaker similarity.

## Current Model Limits

Verified against official provider documentation on 2026-08-09:

| Provider model | Provider language coverage | Ultravox-compatible set |
| --- | ---: | ---: |
| Ultravox Realtime | 26 | 26 |
| Cartesia Sonic 3.5 | 42 | 26 |
| Cartesia Sonic 3 | 42 | 26 |
| Cartesia Sonic 2 | 8 | 7 |
| ElevenLabs Flash v2.5 | 32 | 26 |
| ElevenLabs Multilingual v2 | 29 | 24 |
| ElevenLabs v3 | 70+; 74 currently enumerated | 26 |
| Inworld TTS-2 | 200+ languages/locales; 15 GA plus tested experimental languages | 26 |
| Inworld TTS 1.5 Max/Mini | 15 | 13 |

`documented_language_count_is_minimum` distinguishes `70+` and `200+` from an
exact count. `enumerated_language_count` reports how many base codes Supafone
can explicitly expose from the provider's current documentation.

The API never assumes that an unknown model supports every language. Unknown
provider/model combinations remain discoverable but have `known: false` and
are not recommended as runtime-compatible until their capability is known.

Official references:

- [Ultravox supported languages](https://docs.ultravox.ai/overview)
- [Ultravox voice API](https://docs.ultravox.ai/api-reference/voices/voices-list)
- [Cartesia Sonic 3.5](https://docs.cartesia.ai/build-with-cartesia/tts-models/latest)
- [ElevenLabs models](https://elevenlabs.io/docs/overview/models)
- [Inworld models](https://docs.inworld.ai/tts/tts-models)
- [Inworld multilingual behavior](https://docs.inworld.ai/tts/capabilities/multilingual)

## Inspect Capabilities

```bash
curl "https://api.supafone.ai/api/v1/labs/voices/capabilities" \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"
```

Each provider reports `ultravox_integration` and its known model/language
capabilities. `native` or `named_external` describes the integration route;
`preview_only` does not permit a hosted live-call selection. Account credentials
and a successful call preview are separate checks.

## List and Filter Voices

For the basic provider filter, use the published SDK:

```ts
const page = await supafone.labs.voices.list({ provider: "cartesia" });
console.log(page.voices);
```

```python
page = supafone.labs.voices.list(provider="cartesia")
print(page["voices"])
```

The SDK also accepts advanced filters such as `compatibleLanguage`
(Python `compatible_language`) and `configuredOnly` (Python `configured_only`).
The equivalent REST request is:

```bash
curl --get "https://api.supafone.ai/api/v1/labs/voices" \
  -H "Authorization: Bearer $SUPAFONE_TOKEN" \
  --data-urlencode "provider=cartesia" \
  --data-urlencode "compatible_language=es" \
  --data-urlencode "configured_only=true" \
  --data-urlencode "limit=100"
```

`language` filters a voice's native/accent language. `compatible_language`
filters the intersection of model and Ultravox language support. Available
filters also include `search`, `gender`, `voice_type`, `model`, and
`runtime_provider`. Follow `next_cursor` until it is null to read all pages;
a single SDK `list` request does not automatically paginate.

## Select from Plain Language

The server can rank catalog entries against a description. Use
`labs.voices.recommend({ description: "warm Spanish support voice" })` in
TypeScript, `labs.voices.recommend(description="warm Spanish support voice")`
in Python, or the equivalent REST endpoint:

```bash
curl "https://api.supafone.ai/api/v1/labs/voices/recommend" \
  -H "Authorization: Bearer $SUPAFONE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description":"warm Spanish intake voice","provider":"cartesia","language":"es-MX","configuredOnly":true,"limit":3}'
```

Inspect the returned voice's live-call compatibility before using it. Pass its
provider key, actual `provider_voice_id` (or catalog ID where appropriate), and
model in the managed agent's `voice` object. Do not invent names such as
`sonic-warm` in place of real catalog voice IDs.

```ts
await supafone.labs.agents.createInbound({
  name: "Spanish intake",
  voice: { provider: "cartesia", voiceId: process.env.CARTESIA_VOICE_ID! },
});
```

The same voice object works with `new UltravoxS2S(supafone).create(...)`.
For two to four validated language/voice profiles on the managed runtime, see
[Live Language and Voice Routing](live-language-voice-routing.md).

## Normalized Voice Shape

Every row includes:

- stable IDs: `id`, `provider_voice_id`, `provider_key`;
- runtime identity: `runtime_provider_key`, `synthesis_provider_key`, `model`;
- names: provider display name, voice name, description, and style;
- provider presentation: canonical brand name, logo URL/slug, official site,
  and separate synthesis/runtime brands;
- language: native profiles, model support, runtime intersection, and tier;
- classification: gender, accent, age, voice types, tags, and use cases;
- availability: configured, premium, custom, recommended, and preview flags;
- forward-compatible metadata: `provider_metadata` and
  `provider_metadata_fields`.

Provider metadata is recursively sanitized and bounded. Supafone removes API
keys, credentials, auth headers, tokens, cookies, signatures, binary/audio
payloads, embeddings, emails, and account/user/owner/workspace identifiers
before returning or indexing it.

## Failure Isolation

Provider calls run concurrently. If one provider is unavailable, its error is
reported in `errors` while the other providers and safe fallback voices still
load. Catalog cache keys are account-scoped hashes; raw provider keys are not
returned in responses or written into catalog rows.

## Live Verification Snapshot

The non-secret smoke test on 2026-08-09 loaded 1,386 voices with no provider
errors and no unknown-language rows:

| Source | Voices |
| --- | ---: |
| Ultravox account catalog | 239 |
| Cartesia | 848 |
| ElevenLabs | 24 |
| Inworld | 269 |

It also synthesized real preview audio through Cartesia and Inworld. Counts
are account-specific and will change as providers add or remove voices.
