# One voice router, with a Supervisor

Use **one Agent Factory** for an integrated speech-to-speech model, the existing **Ultravox + external TTS** route, or an independent **STT → LLM → TTS** pipeline. Every route shares the agent's stages, tools, knowledge, Supervisor, Manager, phone assignment and call history.

`SupafoneVoice` is the common superclass. `SupafoneS2S` and all five existing subclasses retain their API. `SupafonePipeline` adds independent speech recognition, reasoning and voice selections. `SupafoneRouter` selects either explicitly; it does not silently switch models or payers.

> **Availability:** these APIs require the matching voice-router backend. Check the live catalog and preflight before starting a call. A model listed as planned or experimental is not certified. A contract test is not a live vendor call. The registry exposes both evidence fields.

## Start with the existing Ultravox route

```python
from supafone_labs import Supafone, SupafoneRouter

client = Supafone()  # reads SUPAFONE_API_KEY
engine = SupafoneRouter(client).select({"kind": "hybrid", "provider": "ultravox"})
agent = engine.create(name="Front desk", supervisor=True)
```

The returned object is an `UltravoxS2S`, preserving external-TTS and original agent settings. Ultravox understands speech directly; no extra STT stage is inserted. Existing native [S2S examples](unified-s2s.md) continue to work.

## Choose each pipeline component

Python:

```python
import os
from supafone_labs import Supafone, SupafonePipeline

client = Supafone(api_key=os.environ["SUPAFONE_API_KEY"])
engine = SupafonePipeline(
    client,
    stt={"provider": "cartesia", "model": "ink-2"},
    llm={"provider": "openai", "model": "gpt-4.1"},
    tts={"provider": "inworld", "model": "inworld-tts-2-flash", "voice": "Dennis"},
    credentials={"default": "auto", "llm": "byok"},
    language="en",
    transport="browser",
)
preflight = engine.validate()
# Inspect preflight readiness and reasons before starting a call.
agent = engine.create(name="Front desk", supervisor=True, manager={"enabled": True})
```

TypeScript:

```ts
import { Supafone, SupafonePipeline } from "supafone-labs";

const client = new Supafone({ apiKey: process.env.SUPAFONE_API_KEY! });
const engine = new SupafonePipeline(client, {
  stt: { provider: "cartesia", model: "ink-2" },
  llm: { provider: "openai", model: "gpt-4.1" },
  tts: { provider: "inworld", model: "inworld-tts-2-flash", voice: "Dennis" },
  credentials: { default: "auto", llm: "byok" },
  language: "en",
  transport: "browser",
});
const preflight = await engine.validate();
const agent = await engine.create({ name: "Front desk", supervisor: true, manager: { enabled: true } });
```

These IDs illustrate a cross-provider selection. Use `client.labs.voice.catalog()` for the deployment's exact models, status and evidence. Choose a voice supported by the selected TTS model. A saved configuration is not a successful audio connection.

`engine.apply(agentKey)` selects the route for **subsequent calls** and keeps the agent's workflow. It clears the previous native selection. Applying an existing S2S adapter clears the pipeline on the server. `test_call` / `testCall` previews the saved route and never applies a switch implicitly. Active-call switching remains a separate explicit handoff feature.

## One Supafone key, or bring each provider key

| Mode | Whose upstream credential is selected |
| --- | --- |
| `auto` | Saved account profile when present; otherwise configured Supafone profile |
| `managed` | Supafone's enabled platform profile |
| `byok` | Required encrypted account profile; never silently fall back to managed billing |

Select modes independently for STT, LLM and TTS. The Supervisor and Manager keep their own reasoning settings. The TTS provider does not receive the LLM or Supervisor key.

Store credentials through the account profile endpoint, **never in pipeline JSON**:

```python
client.labs.voice.configure_profile(
    "openai", "llm", profile="default", mode="byok",
    credentials={"api_key": os.environ["OPENAI_API_KEY"]},
)
status = client.labs.voice.get_profile("openai", "llm")
```

```ts
await client.labs.voice.configureProfile("openai", "llm", {
  mode: "byok", credentials: { api_key: process.env.OPENAI_API_KEY! },
});
const status = await client.labs.voice.getProfile("openai", "llm");
```

Profiles are scoped to account, provider, service and profile name. Set a component's `profile` field to select a named profile. Saving managed mode removes that saved override for future calls using the profile. Masked profile status contains no secrets. Cloud providers may need project, region, resource and workload credentials rather than one API-key string. Preflight reports unsupported profile/runtime requirements. BYOK still uses Supafone orchestration and transport resources.

## Every combination, with explicit evidence

The registry enumerates the **full STT × LLM × TTS product**, including unsupported tuples with reasons. Selecting an STT does not limit the LLM or TTS to its vendor. Integrated S2S and Ultravox hybrid routes are counted separately.

```python
page = client.labs.voice.combinations(
    context={"language": "en", "transport": "browser", "requires_tools": True},
    offset=0, limit=100,
)
# Request next_offset until it is null; keep registry_hash unchanged across pages.
```

The response separates raw candidates, compatibility, credential readiness and certification evidence. Missing keys affect readiness, not composability. `planned`, `experimental`, `certified`, `deprecated` and `retired` are catalog states. `contract_verified` and `live_verified` describe separate checks; neither may be inferred from a provider logo or endpoint listing. `voice_catalog_snapshot()` / `voiceCatalogSnapshot()` returns the packaged discovery snapshot; the live API remains authoritative.

## CLI

Save the pipeline constructor options above as `pipeline.json` (no credentials):

```sh
supafone router schema
supafone router catalog --layer stt --json
supafone router combinations --all --explain --json
supafone pipeline validate --config-file pipeline.json
supafone router profile set --provider openai --service llm --mode byok --api-key-env OPENAI_API_KEY
supafone agents create --name "Front desk" --pipeline-file pipeline.json --supervisor managed --manager managed
supafone pipeline apply front-desk --config-file pipeline.json
supafone pipeline test-call front-desk
```

For cloud credentials, use `--credentials-env NAME_OF_JSON_ENVIRONMENT_VARIABLE`. No provider secret is accepted as a literal CLI flag. `router apply` accepts a tagged route such as `{"kind":"hybrid","provider":"ultravox"}` or `{"kind":"pipeline","pipeline":{...}}`. `pipeline` is a convenience command group for the composed route.

## Configuration contract

- `schema_version`: `1` (default).
- `stt`, `llm`, `tts`: independent `{provider, model, profile?, options?}` objects. Only `tts` accepts `voice`.
- `credentials`: optional `default`, `stt`, `llm`, `tts` modes.
- Optional `language`, `region`, `transport` context.
- `realtime` and a non-null `pipeline` are mutually exclusive.
- Unknown models, incompatible capabilities and missing credentials fail preflight. Selection does not trigger paid connections.
- `options` accepts only documented scalar controls. Credentials and arbitrary endpoints cannot be smuggled into saved configuration.
- No automatic fallback, vendor substitution or payer change is enabled by these constructors.
