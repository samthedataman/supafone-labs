# Call Stages

Call stages keep agents from behaving like one giant prompt. Supafone should
generate stages by default from the smallest useful metadata: title, direction,
industry, website URL, goal, and system prompt.

## Developer Default

For common agents, the developer should not have to write stages by hand.

```ts
await supafone.labs.agents.createInboundWithNumber({
  agentKey: "northline-intake",
  name: "Northline intake",
  systemPrompt: "Warm personal-injury intake. Never quote fees. Book consults.",
  runtimeMode: "multi_stage",
  presetKey: "general_intake_receptionist",
  labs: { enabled: true, model: "gemma" },
});
```

If `runtimeMode` is omitted, the hosted API default contract is multi-stage.
The SDK helpers also default the preset:

| Helper | Default direction | Default preset |
| --- | --- | --- |
| `createInbound()` | `inbound` | `general_intake_receptionist` |
| `createInboundWithNumber()` | `inbound` | `general_intake_receptionist` |
| `createOutbound()` | `outbound` | `speed_to_lead_caller` |
| `createOutboundWithNumber()` | `outbound` | `speed_to_lead_caller` |

## UI Shorthand

The builder can expose a simple switch:

```json
{
  "callStages": true
}
```

Until `callStages` is a first-class SDK field, the frontend should compile that
switch into:

```json
{
  "runtimeMode": "multi_stage",
  "presetKey": "general_intake_receptionist"
}
```

For outbound:

```json
{
  "runtimeMode": "multi_stage",
  "presetKey": "speed_to_lead_caller"
}
```

## Generated Stage Shape

A generated inbound intake plan should look like this conceptually:

```json
{
  "stages": [
    {
      "key": "opening",
      "goal": "Greet the caller, identify the reason for calling, and set expectations."
    },
    {
      "key": "qualification",
      "goal": "Collect the core facts needed to route or book the call."
    },
    {
      "key": "resolution",
      "goal": "Book, route, send a follow-up, or complete the requested task."
    },
    {
      "key": "confirmation",
      "goal": "Confirm next step, timing, and contact method."
    }
  ]
}
```

The runtime already supports stage transitions and adapter-specific stage
updates. Providers that support stageful updates receive native state updates;
providers that do not receive a compact context injection.

## Customization

Developers can customize without losing convenience:

```ts
await supafone.labs.agents.createInbound({
  agentKey: "vip-intake",
  name: "VIP intake",
  runtimeMode: "multi_stage",
  presetKey: "general_intake_receptionist",
  metadata: {
    stagePlan: {
      stages: ["opening", "eligibility", "handoff", "confirmation"]
    }
  }
});
```

The API should treat custom stages as an override to the generated plan, not as
a requirement for every agent.
