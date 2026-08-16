# Describe the Call. Supafone Builds the Plan.

Most voice agents begin as one enormous prompt. That works in a demo, then
falls apart when a real caller interrupts, changes topics, or asks the agent to
take an action.

Supafone turns one plain-English description into a production call program:
an agent-wide prompt, three to eight focused stages, exit criteria, tool rules,
safe transitions, and a final close. The exact plan returned to your code is
the exact plan stored on the agent and executed during calls.

## Why developers care

- **Write the business intent once.** You do not have to become a prompt
  engineer before shipping a receptionist or outbound caller.
- **Use one Supafone key.** Supafone keeps its Haiku/OpenRouter credential on
  the server; it never appears in your browser, app, MCP config, or logs.
- **Preview before provisioning.** Generate the plan, show it in your UI,
  edit any stage, and send the reviewed version back as an explicit override.
- **Avoid demo-only prompts.** Each stage includes an observable completion
  condition and rules for tools, claims, escalation, and transitions.
- **Keep shipping when a model is unavailable.** Invalid or unavailable model
  output falls back to a safe Supafone template instead of breaking creation.
- **Own the result.** Generated stages are ordinary JSON. Store, diff, review,
  test, or replace them without locking your application to a hidden prompt.

## Why customers notice

- The agent asks one useful question at a time.
- It remembers what the caller already said instead of restarting intake.
- It does not claim a booking, transfer, message, or CRM update succeeded until
  the corresponding tool confirms it.
- Outbound agents identify themselves, explain the purpose, and honor opt-outs.
- Legal and medical agents receive industry-specific safety instructions.
- The close accurately summarizes what was actually confirmed.

## The shortest path

TypeScript:

```ts
const agent = await supafone.labs.agents.createOutbound({
  name: "Warm lead follow-up",
  businessName: "Northline Roofing",
  description: "Call homeowners who requested an estimate, qualify the job, and book a site visit.",
  direction: "outbound",
  tools: { scheduling: true, sms: true },
});

console.log(agent.call_plan?.generated_by); // supafone_hosted_haiku
console.log(agent.call_plan?.call_stages);  // the stages now running on the agent
```

Python:

```python
agent = supafone.labs.agents.create_outbound({
    "name": "Warm lead follow-up",
    "businessName": "Northline Roofing",
    "description": "Call homeowners who requested an estimate, qualify the job, and book a site visit.",
    "tools": {"scheduling": True, "sms": True},
})

print(agent["call_plan"]["generated_by"])
```

Creation defaults to the hosted planner. No Anthropic or OpenRouter key is
accepted by this method.

## Preview and edit before creation

```ts
const plan = await supafone.generateCallStages({
  name: "Patient scheduler",
  description: "Answer appointment calls, identify urgent symptoms, and schedule the correct visit type.",
  industry: "medical",
  direction: "inbound",
  stageCount: 5,
  stageDetail: "detailed",
  tools: { scheduling: true, emergencyEscalation: true },
});

// It is normal JSON—let an administrator review or edit it.
plan.call_stages[1].instructions += " Confirm whether this is a new or existing patient.";

const agent = await supafone.labs.agents.createInbound({
  name: "Patient scheduler",
  businessName: "Northline Clinic",
  callStages: plan.call_stages,
});
```

The MCP exposes the same operation as `generate_call_stages`. Claude, Codex,
Cursor, and other MCP clients can generate the plan and present it for review
without receiving your provider credentials.

## Modes

| Setting | What happens | Best for |
| --- | --- | --- |
| omitted or `oracle` | Supafone generates and validates the complete plan | Normal production use |
| `template` | Supafone uses the deterministic offline template | Tests and fixed-cost environments |
| explicit stage array | Supafone validates and executes exactly what you supplied | Reviewed or regulated workflows |
| `off` / `false` | No generated override; the product's built-in staged default remains | Legacy compatibility |

```ts
await supafone.labs.agents.createInbound({
  name: "Reviewed intake",
  stageGeneration: "template", // or "oracle" / "off"
  stageCount: 4,                 // 3-8
  stageDetail: "standard",
});
```

## What comes back

```json
{
  "version": "supafone_call_plan_v1",
  "summary": "Five-stage inbound scheduling plan",
  "base_system_prompt": "Agent-wide behavior and safety rules...",
  "generated_by": "supafone_hosted_haiku",
  "model": "anthropic/claude-3-haiku-20240307",
  "fallback": false,
  "call_stages": [
    {
      "key": "discovery",
      "name": "Focused discovery",
      "goal": "Understand the caller's request without repeating known facts.",
      "instructions": "Complete stage-level prompt...",
      "exit_criteria": ["The required facts are explicitly confirmed"],
      "tools": ["query_knowledge", "save_lead"],
      "temperature": 0.3,
      "next_stages": ["confirmed_action"]
    }
  ]
}
```

`fallback: true` is transparent: the request still succeeds, and your UI can
tell an administrator that Supafone used the safe template instead of the
hosted model.

## Security boundary

The SDK sends only bounded planning context: description, direction, industry,
goal, business/agent name, enabled tool categories, and optional existing
prompt. Telephony tokens, Ultravox keys, TTS keys, SMTP passwords, and other
BYOK secrets are deliberately excluded from the planner request.

Next: [Agent Factory](agent-factory.md) · [MCP Server](mcp-server.md) ·
[Hosted Agents API](hosted-agents-api.md)
