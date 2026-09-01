# Managed and BYOK Supervisor Models

The Supafone Supervisor is the independent reasoning model that watches a live
agent off the audio path. It is not the speech-to-speech model talking to the
caller. Keep OpenAI Realtime, Gemini Live, Grok Voice, Ultravox, Vapi, Retell,
or another supported speaking runtime and choose the Supervisor separately.

## Choose managed or BYOK

| Mode | Key required | Models | Best for |
| --- | --- | --- | --- |
| Supafone managed | No | `supafone-supervisor`, `supafone-supervisor-pro` | Agent Factory and teams that want one Supafone key |
| BYOK Anthropic | `ANTHROPIC_API_KEY` | Any compatible Claude Messages model | Existing Anthropic accounts |
| BYOK OpenAI | `OPENAI_API_KEY` | Any compatible Responses API model | Existing OpenAI accounts |
| BYOK Gemini | `GEMINI_API_KEY` | Any compatible Gemini `generateContent` model | Existing Google AI accounts |
| BYOK OpenRouter | `OPENROUTER_API_KEY` | Any compatible OpenRouter chat model | One key across many model vendors |
| BYOK Groq | `GROQ_API_KEY` | Any compatible Groq chat model | Low-latency open-model inference |
| BYOK Cerebras | `CEREBRAS_API_KEY` | Any compatible Cerebras chat model | High-throughput open-model inference |

Managed supervision is included in metered Agent Factory runtime. Supafone owns
the model credential and selects the provider behind each stable model alias.
BYOK inference is charged by the selected provider; Supafone still meters any
managed call, telephony, speech, storage, or other infrastructure used by the
agent.

Provider keys are submitted to the Supafone API over HTTPS, encrypted before
storage, and never returned. API responses expose only
`api_key_configured: true|false`. The CLI accepts the *name* of an environment
variable and never accepts or prints the key itself.

## Managed Agent Factory model

Python:

```python
import os
from supafone_labs import Supafone

supafone = Supafone(api_key=os.environ["SUPAFONE_API_KEY"])
agent = supafone.labs.agents.create_inbound({
    "name": "Northline intake",
    "business_name": "Northline Health",
    "supervisor": {
        "enabled": True,
        "mode": "managed",
        "model": "supafone-supervisor",
    },
})
print(agent["agent"]["agent_key"])
```

TypeScript:

```typescript
import { Supafone } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_API_KEY! });
const agent = await supafone.labs.agents.createInbound({
  name: "Northline intake",
  businessName: "Northline Health",
  supervisor: {
    enabled: true,
    mode: "managed",
    model: "supafone-supervisor",
  },
});
console.log(agent.agent.agent_key);
```

Use `supafone-supervisor-pro` when the call requires the deeper managed model.
Set `supervisor: false` to create a raw agent without live supervision.

## BYOK provider configurations

The Agent Factory call is identical for every provider. Select one configuration
below and pass it as `supervisor`.

=== "Claude"

    ```python
    supervisor = {
        "enabled": True,
        "mode": "byok",
        "provider": "anthropic",
        "model": "claude-haiku-4-5-20251001",
        "api_key": os.environ["ANTHROPIC_API_KEY"],
    }
    ```

=== "OpenAI"

    ```python
    supervisor = {
        "enabled": True,
        "mode": "byok",
        "provider": "openai",
        "model": "gpt-5-mini",
        "api_key": os.environ["OPENAI_API_KEY"],
    }
    ```

=== "Gemini"

    ```python
    supervisor = {
        "enabled": True,
        "mode": "byok",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "api_key": os.environ["GEMINI_API_KEY"],
    }
    ```

=== "OpenRouter"

    ```python
    supervisor = {
        "enabled": True,
        "mode": "byok",
        "provider": "openrouter",
        "model": "anthropic/claude-haiku-4.5",
        "api_key": os.environ["OPENROUTER_API_KEY"],
    }
    ```

=== "Groq"

    ```python
    supervisor = {
        "enabled": True,
        "mode": "byok",
        "provider": "groq",
        "model": "llama-3.1-8b-instant",
        "api_key": os.environ["GROQ_API_KEY"],
    }
    ```

=== "Cerebras"

    ```python
    supervisor = {
        "enabled": True,
        "mode": "byok",
        "provider": "cerebras",
        "model": "gpt-oss-120b",
        "api_key": os.environ["CEREBRAS_API_KEY"],
    }
    ```

Complete Python call:

```python
import os
from supafone_labs import Supafone

supafone = Supafone(api_key=os.environ["SUPAFONE_API_KEY"])
agent = supafone.labs.agents.create_inbound({
    "name": "BYOK supervised intake",
    "supervisor": supervisor,  # choose one configuration above
})
```

Complete TypeScript call (change the provider, model, and environment variable
using the table above):

```typescript
import { Supafone } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_API_KEY! });
const agent = await supafone.labs.agents.createInbound({
  name: "BYOK supervised intake",
  supervisor: {
    enabled: true,
    mode: "byok",
    provider: "gemini",
    model: "gemini-2.5-flash",
    apiKey: process.env.GEMINI_API_KEY!,
  },
});
```

REST:

```bash
curl https://api.supafone.ai/api/v1/labs/agents \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg key \"$OPENROUTER_API_KEY\" \
    '{
      name: "OpenRouter supervised intake",
      style: "inbound",
      supervisor: {
        enabled: true,
        mode: "byok",
        provider: "openrouter",
        model: "anthropic/claude-haiku-4.5",
        api_key: $key
      }
    }')"
```

CLI:

```bash
supafone agents create --name "Managed intake" --supervisor managed
supafone agents create --name "Claude intake" --supervisor anthropic
supafone agents create --name "OpenAI intake" --supervisor openai
supafone agents create --name "Gemini intake" --supervisor gemini
supafone agents create --name "OpenRouter intake" --supervisor openrouter
supafone agents create --name "Groq intake" --supervisor groq
supafone agents create --name "Cerebras intake" --supervisor cerebras
```

Each BYOK command reads the conventional provider environment variable shown in
the table. Override the variable name without exposing its value:

```bash
supafone agents create \
  --name "Custom Gemini intake" \
  --supervisor gemini \
  --supervisor-model gemini-2.5-flash \
  --supervisor-api-key-env MY_GEMINI_KEY
```

## Runtime behavior

1. The speaking runtime continues handling caller audio.
2. Supafone normalizes transcript, tool, stage, language, and policy events.
3. The selected managed or BYOK Supervisor returns a structured candidate directive.
4. Confidence, policy, cooldown, and tool-truth gates may suppress it.
5. A provider adapter silently injects an accepted directive when that speaking
   runtime exposes a supported control surface.
6. Any Supervisor timeout or provider error produces no directive; the call
   continues without waiting.

Supafone uses fixed provider-owned API endpoints for BYOK inference. This keeps
the credential contract explicit and prevents arbitrary callback URLs from
becoming server-side request targets.

The provider produces the same canonical directive packet regardless of model:
`empathy_directive`, `tactical_directive`, `surface_facts`, `guardrails`,
`language`, `confidence`, and `kind`. These correspond to a human supervisor's
interpersonal response, next operational move, observed evidence, policy
boundaries, language choice, intervention threshold, and guidance category.
Read [Programmable Supervisor Directives](https://github.com/samthedataman/supafone-labs/blob/main/gitbook/programmable-supervisor-directives.md)
for the field-level contract and safety gate.

## Provider references

- [Anthropic Messages API](https://platform.claude.com/docs/en/api/messages/create)
- [OpenAI Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [Gemini generateContent API](https://ai.google.dev/api/generate-content)
- [OpenRouter chat completions](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request)
- [Groq chat completions](https://console.groq.com/docs/api-reference)
- [Cerebras chat completions](https://inference-docs.cerebras.ai/api-reference/chat-completions)
