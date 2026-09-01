# Supervisor Models: Managed and BYOK

The **speaking model** owns caller audio. The **Supervisor model** reasons beside
the call and proposes bounded silent guidance. They are independent: an OpenAI
Realtime, Gemini Live, Grok Voice, Ultravox, Vapi, or Retell agent can use any
supported managed or BYOK Supervisor model below.

## Managed models

Paid Agent Factory customers do not need another model key:

| Model | Purpose |
| --- | --- |
| `supafone-supervisor` | Fast managed supervision for normal production calls |
| `supafone-supervisor-pro` | Deeper managed reasoning for higher-risk workflows |

```typescript
const agent = await supafone.labs.agents.createInbound({
  name: "Northline intake",
  supervisor: {
    enabled: true,
    mode: "managed",
    model: "supafone-supervisor"
  }
});
```

## BYOK providers

| Provider | Value | Suggested starting model | Key environment variable |
| --- | --- | --- | --- |
| Claude | `anthropic` | `claude-haiku-4-5-20251001` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai` | `gpt-5-mini` | `OPENAI_API_KEY` |
| Gemini | `gemini` | `gemini-2.5-flash` | `GEMINI_API_KEY` |
| OpenRouter | `openrouter` | `anthropic/claude-haiku-4.5` | `OPENROUTER_API_KEY` |
| Groq | `groq` | `llama-3.1-8b-instant` | `GROQ_API_KEY` |
| Cerebras | `cerebras` | `gpt-oss-120b` | `CEREBRAS_API_KEY` |

Supafone encrypts the key before storing the agent. Read responses expose only
`api_key_configured`; they never return plaintext or ciphertext.

## Python

```python
import os
from supafone_labs import Supafone

supafone = Supafone(api_key=os.environ["SUPAFONE_API_KEY"])

provider_configs = {
    "anthropic": {
        "provider": "anthropic",
        "model": "claude-haiku-4-5-20251001",
        "api_key": os.environ["ANTHROPIC_API_KEY"],
    },
    "openai": {
        "provider": "openai",
        "model": "gpt-5-mini",
        "api_key": os.environ["OPENAI_API_KEY"],
    },
    "gemini": {
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "api_key": os.environ["GEMINI_API_KEY"],
    },
    "openrouter": {
        "provider": "openrouter",
        "model": "anthropic/claude-haiku-4.5",
        "api_key": os.environ["OPENROUTER_API_KEY"],
    },
    "groq": {
        "provider": "groq",
        "model": "llama-3.1-8b-instant",
        "api_key": os.environ["GROQ_API_KEY"],
    },
    "cerebras": {
        "provider": "cerebras",
        "model": "gpt-oss-120b",
        "api_key": os.environ["CEREBRAS_API_KEY"],
    },
}

selected = provider_configs["gemini"]
agent = supafone.labs.agents.create_inbound({
    "name": "BYOK supervised intake",
    "supervisor": {
        "enabled": True,
        "mode": "byok",
        **selected,
    },
})
```

## TypeScript

```typescript
import { Supafone } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_API_KEY! });

const providers = {
  anthropic: { provider: "anthropic", model: "claude-haiku-4-5-20251001", apiKey: process.env.ANTHROPIC_API_KEY! },
  openai: { provider: "openai", model: "gpt-5-mini", apiKey: process.env.OPENAI_API_KEY! },
  gemini: { provider: "gemini", model: "gemini-2.5-flash", apiKey: process.env.GEMINI_API_KEY! },
  openrouter: { provider: "openrouter", model: "anthropic/claude-haiku-4.5", apiKey: process.env.OPENROUTER_API_KEY! },
  groq: { provider: "groq", model: "llama-3.1-8b-instant", apiKey: process.env.GROQ_API_KEY! },
  cerebras: { provider: "cerebras", model: "gpt-oss-120b", apiKey: process.env.CEREBRAS_API_KEY! },
} as const;

const agent = await supafone.labs.agents.createInbound({
  name: "BYOK supervised intake",
  supervisor: {
    enabled: true,
    mode: "byok",
    ...providers.gemini,
  },
});
```

## REST

```bash
curl https://api.supafone.ai/api/v1/labs/agents \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg key \"$OPENROUTER_API_KEY\" '{
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

## CLI

```bash
supafone agents create --name "Managed intake" --supervisor managed
supafone agents create --name "Claude intake" --supervisor anthropic
supafone agents create --name "OpenAI intake" --supervisor openai
supafone agents create --name "Gemini intake" --supervisor gemini
supafone agents create --name "OpenRouter intake" --supervisor openrouter
supafone agents create --name "Groq intake" --supervisor groq
supafone agents create --name "Cerebras intake" --supervisor cerebras
```

The CLI reads the conventional provider environment variable. To use another
variable name, pass `--supervisor-api-key-env MY_KEY`; do not put the key itself
on the command line.

## What happens at runtime

1. Supafone normalizes transcript, language, stage, tool, and policy events.
2. The selected Supervisor returns a structured candidate directive.
3. Confidence, policy, cooldown, and tool-truth gates may suppress it.
4. An adapter injects an accepted directive through the speaking runtime's
   supported hidden control surface.
5. A timeout or provider failure produces no directive. The speaking agent never
   waits for supervision.

Every provider must produce the same inspectable packet: interpersonal guidance
(`empathy_directive`), the next operational move (`tactical_directive`), observed
evidence (`surface_facts`), truth and policy boundaries (`guardrails`), language,
confidence, and guidance kind. The deterministic gate and provider adapter sit
after model inference, so switching reasoning providers cannot bypass them. See
[Programmable Supervisor Directives](programmable-supervisor-directives.md) for
the human-supervisor mapping and field-level controls.

The server uses fixed official endpoints for each provider:
[Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create),
[OpenAI Responses](https://developers.openai.com/api/reference/resources/responses/methods/create),
[Gemini generateContent](https://ai.google.dev/api/generate-content),
[OpenRouter chat completions](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request),
[Groq chat completions](https://console.groq.com/docs/api-reference), and
[Cerebras chat completions](https://inference-docs.cerebras.ai/api-reference/chat-completions).
