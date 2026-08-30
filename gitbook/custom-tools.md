# Custom tools

Custom tools let an inbound or outbound Supafone agent call your CRM, scheduling service, order system, or automation webhook during a live conversation. They are executable tools, not prompt hints. For an agent-owned email sender, use the first-class [SMTP and email tool](smtp-and-email.md).

## Define a tool

Register the tool inside `tools.customTools` when you create the agent:

{% tabs %}
{% tab title="TypeScript" %}
```typescript
import { Supafone } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_API_KEY! });

const agent = await supafone.labs.agents.createInbound({
  name: "Order support",
  businessName: "Acme",
  tools: {
    customTools: [{
      name: "lookup_order",
      description: "Look up an order after the caller confirms the order number.",
      url: "https://api.acme.example/supafone/order",
      header: "X-API-Key",
      apiKey: process.env.ACME_TOOL_KEY,
      params: [
        { name: "order_id", type: "string", required: true },
        { name: "include_history", type: "boolean" },
      ],
      stages: ["support", "confirmation"],
    }],
  },
});
```
{% endtab %}

{% tab title="Python" %}
```python
import os
from supafone_labs import Supafone

supafone = Supafone(api_key=os.environ["SUPAFONE_API_KEY"])

agent = supafone.labs.agents.create_inbound({
    "name": "Order support",
    "businessName": "Acme",
    "tools": {
        "customTools": [{
            "name": "lookup_order",
            "description": "Look up an order after the caller confirms the order number.",
            "url": "https://api.acme.example/supafone/order",
            "header": "X-API-Key",
            "apiKey": os.environ["ACME_TOOL_KEY"],
            "params": [
                {"name": "order_id", "type": "string", "required": True},
                {"name": "include_history", "type": "boolean"},
            ],
            "stages": ["support", "confirmation"],
        }],
    },
})
```
{% endtab %}
{% endtabs %}

The MCP hosted-agent creation tools accept the same object under `tools.customTools`. REST uses the same shape at `POST /api/v1/labs/agents`; snake-case aliases are also accepted.

## Webhook request

Supafone sends one `POST` request with only the declared arguments and bounded call context:

```json
{
  "params": {
    "order_id": "A-1042",
    "include_history": false
  },
  "context": {
    "agent_id": "agt_...",
    "business_name": "Acme",
    "call_record_id": "call_...",
    "call_sid": "CA...",
    "stage": "support"
  }
}
```

Return JSON or plain text. Supafone caps the response and gives it to the model as untrusted data. The model cannot use the response as a new system instruction.

## Runtime and security contract

- Tool names are unique lowercase identifiers and cannot shadow built-in tools.
- Parameters support `string`, `number`, `integer`, and `boolean`.
- `stages` is optional. When present, the tool does not exist outside those stages.
- The endpoint must use HTTPS. Redirects and private, loopback, link-local, metadata, and non-public DNS targets are rejected in production.
- Supafone resolves and pins the vetted public address to prevent DNS rebinding.
- The optional API key is encrypted at rest, attached only by Supafone's proxy, and never returned by the API or sent to the speaking model.
- Calls are rate-limited, time-bounded, and response-size bounded. A failed tool returns a safe unavailable result and does not crash the call.
- The supervisor consumes the resulting `tool.called` and `tool.result` truth events, so the agent must not claim success until the endpoint confirms it.

## Limits

Each agent can define up to 10 custom tools with up to 8 parameters per tool. Custom tools currently use server-side HTTP `POST`; arbitrary client-side code is never executed in the voice runtime.
