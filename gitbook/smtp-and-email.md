# SMTP and email tools

An inbound or outbound Supafone agent can send approved email during a call through its own SMTP account. SMTP is optional: when it is absent, the agent can use an account-level sender if one is configured; otherwise `send_email` is not exposed to the speaking model.

## Configure an inbound agent

{% tabs %}
{% tab title="TypeScript" %}
```typescript
const agent = await supafone.labs.agents.createInbound({
  name: "Acme support",
  tools: { email: true },
  email: {
    enabled: true,
    fromEmail: "support@acme.example",
    smtpHost: "smtp.acme.example",
    smtpPort: 587,
    smtpUser: "support@acme.example",
    smtpPassword: process.env.ACME_SMTP_PASSWORD,
  },
});
```
{% endtab %}

{% tab title="Python" %}
```python
agent = supafone.labs.agents.create_inbound({
    "name": "Acme support",
    "tools": {"email": True},
    "email": {
        "enabled": True,
        "fromEmail": "support@acme.example",
        "smtpHost": "smtp.acme.example",
        "smtpPort": 587,
        "smtpUser": "support@acme.example",
        "smtpPassword": os.environ["ACME_SMTP_PASSWORD"],
    },
})
```
{% endtab %}
{% endtabs %}

The same payload works with `POST /api/v1/labs/agents` and the MCP `create_inbound_agent` or `create_outbound_agent` tools. REST also accepts snake-case field names.

## What the runtime does

1. Supafone encrypts the SMTP password before storing the agent.
2. Agent reads return only a masked password sentinel.
3. At inbound-call creation, the runtime verifies that either the agent or its account has a usable sender.
4. Only then does it compile `send_email` into the live agent's allowed tools.
5. The model collects a recipient address, subject, and plain-text body.
6. Supafone sends the message and returns the real delivery result to the call.
7. The agent may claim the email was sent only after that result succeeds.

Disabling `tools.email` removes the capability even when SMTP is configured. Disabling the `email` configuration keeps the credentials stored but makes the agent fall back to the account sender or no email tool.

## Inbound readiness

For an inbound phone agent to be ready, the agent must be created, active, and assigned to a tenant-owned number whose inbound webhook resolves to that agent. SMTP does not control whether the phone answers; it only controls whether the verified `send_email` action is available during that call.

Managed numbers are purchased into the developer tenant's isolated carrier subaccount. Supafone never lists or reassigns parent-account client numbers as developer inventory.
