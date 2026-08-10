# Dynamic Voice Catalog and Selection

Supafone exposes one normalized voice catalog across Ultravox, Cartesia,
ElevenLabs, and Inworld. Developers can discover the voices their account can
actually use, filter them with stable fields, preview them, or ask Supafone to
select one from a plain-language description.

The catalog is live. Supafone pages each connected provider API to exhaustion,
normalizes the results, and caches the account-scoped result for 10 minutes.
Provider additions therefore appear without an SDK release.

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

TypeScript:

```ts
const capabilities = await supafone.labs.voices.capabilities();

for (const provider of capabilities.providers) {
  for (const model of provider.models) {
    console.log(
      provider.provider,
      model.model,
      model.documented_language_count,
      model.ultravox_routing_language_count,
    );
  }
}
```

Python:

```python
capabilities = supafone.labs.voices.capabilities()
for provider in capabilities["providers"]:
    for model in provider["models"]:
        print(
            provider["provider"],
            model["model"],
            model["documented_language_count"],
            model["ultravox_routing_language_count"],
        )
```

## List and Filter Voices

`language` means the voice's native/accent language. `compatibleLanguage`
means the provider model and Ultravox can both run that language live.

```ts
const catalog = await supafone.labs.voices.listAll({
  provider: "cartesia",
  language: "es-MX",
  compatibleLanguage: "es",
  gender: "female",
  voiceType: "customer_support",
  model: "sonic-3.5",
  configuredOnly: true,
});
```

```python
catalog = supafone.labs.voices.list_all(
    provider="cartesia",
    language="es-MX",
    compatible_language="es",
    gender="female",
    voice_type="customer_support",
    model="sonic-3.5",
    configured_only=True,
)
```

Available filters are `provider`, `search`, `language`,
`compatible_language`, `gender`, `voice_type`, `model`, `runtime_provider`,
and `configured_only`. The endpoint is cursor-paginated; `listAll()` and
`list_all()` safely follow every page.

## Select from Plain Language

Supafone searches both normalized fields and sanitized provider-native
metadata. This means new provider labels, accent descriptors, use cases, and
categories become searchable without adding a new regex for every field.

```ts
const result = await supafone.labs.voices.recommend({
  description: "warm Puerto Rican Spanish female intake voice",
  language: "es-PR",
  voiceType: "warm_empathetic",
  configuredOnly: true,
  limit: 3,
});

const selected = result.matches[0].voice;
await supafone.labs.agents.createInbound({
  name: "Spanish intake",
  voice: supafone.labs.voices.selection(selected),
});
```

Agent Factory can resolve the preference in one request:

```python
agent = supafone.labs.agents.create_inbound({
    "name": "Hindi patient intake",
    "preferredLanguage": "hi-IN",
    "voicePreference": {
        "description": "calm Hindi patient-support voice",
        "provider": "inworld",
        "configuredOnly": True,
    },
})
```

The backend stores the exact selected provider, voice ID, model, and fixed
language hint. `preferredLanguage` applies for the whole call and supplies the
default language filter for `voicePreference`. It does not enable live
language or voice switching. Existing agents that specify a voice directly
keep their current behavior; preference resolution is additive.

## Normalized Voice Shape

Every row includes:

- stable IDs: `id`, `provider_voice_id`, `provider_key`;
- runtime identity: `runtime_provider_key`, `synthesis_provider_key`, `model`;
- names: provider display name, voice name, description, and style;
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
