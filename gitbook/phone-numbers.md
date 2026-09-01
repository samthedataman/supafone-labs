# Phone Numbers

Supafone-hosted agents support three Supafone-managed number strategies plus a
BYOK carrier path.

## Strategies

| Strategy | Monthly price | Behavior |
| --- | ---: | --- |
| `default_pool` | `$0` | Use an idle shared Supafone number for dev, demos, and early traffic. |
| `dedicated` | `$3.00` per number-month | Reserve a standard number in the account's isolated carrier subaccount. |
| `premium` | `$3.00` per number-month | Reserve premium inventory in the same isolated carrier subaccount. |
| `byok` | `$0` Supafone number rent | Use customer-owned Twilio, Telnyx, Plivo, SIP, or similar credentials. |

Shared-pool numbers are explicitly designated testing routes; Supafone never
reuses customer production lines as pool inventory. Dedicated and premium
numbers require a paid Stripe entitlement before Supafone creates or reuses the
developer tenant's isolated carrier subaccount, purchases the number, configures
webhooks, and assigns it to an agent.

## Search Shared Pool or Inventory

Search finds a route for agent creation. To inspect the live, explicitly
enrolled developer pool itself, use the pool endpoint:

```bash
curl https://api.supafone.ai/api/v1/labs/phone-numbers/pool \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"
```

The snapshot includes counts and per-number `available`, `status`, `reason`,
`health`, and capability fields. Status is one of `available`, `in_use`,
`cooldown`, `reserved`, or `unavailable`. Only `available` numbers are green;
all other states are unavailable for a new shared route.

TypeScript:

```ts
const snapshot = await supafone.labs.phoneNumbers.pool();
console.log(snapshot.counts.available);

const socket = await supafone.labs.phoneNumbers.connectPool();
socket.addEventListener("message", (event) => {
  console.log(JSON.parse(event.data));
});
```

Python:

```python
snapshot = supafone.labs.phone_numbers.pool()
print(snapshot["counts"]["available"])

async for event in supafone.labs.phone_numbers.stream_pool():
    print(event)
```

Python realtime streaming requires the optional `websockets` dependency;
install `supafone-labs[stt]` or `supafone-labs[all]`.

CLI:

```bash
supafone numbers pool
supafone numbers watch --events 10
```

The REST snapshot exchanges the API key for a short-lived, pool-only WebSocket
token. SDKs put that scoped token, never the full API key, in the stream URL.
The response can contain only operator-enrolled developer routes; it does not
infer customer-owned or merely unassigned numbers into the pool. Live status is
availability telemetry, not ownership or a promise that a later claim cannot
lose a race.

```ts
const results = await supafone.labs.phoneNumbers.search({
  areaCode: "415",
  limit: 3,
  numberStrategy: "default_pool"
});
```

```bash
curl https://api.supafone.ai/api/v1/labs/phone-numbers/search \
  -X POST \
  -H "Authorization: Bearer $SUPAFONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "area_code": "415",
    "limit": 3,
    "number_strategy": "default_pool"
  }'
```

## Explicit Dedicated Purchase

Use this only after the account has chosen a `$3/month` dedicated number. The SDK
returns Stripe Checkout first and provisions only after that checkout is paid.

```ts
await supafone.labs.phoneNumbers.buy({
  phoneNumber: "+14155550123",
  friendlyName: "Main intake line",
  agentKey: "northline-phone",
  numberStrategy: "dedicated",
  telephony: { mode: "supafone_managed", provider: "supafone" }
});
```

## Explicit Premium Purchase

Use this only after the account has chosen a `$3/month` premium number.

```ts
await supafone.labs.phoneNumbers.buy({
  phoneNumber: "+14155550123",
  friendlyName: "Premium sales line",
  agentKey: "northline-sales",
  numberStrategy: "premium",
  premium: true,
  telephony: { mode: "supafone_managed", provider: "supafone" }
});
```

## Assign Existing Number

```ts
await supafone.labs.phoneNumbers.assign("num_123", {
  agentKey: "northline-intake",
  style: "inbound",
  presetKey: "general_intake_receptionist"
});
```

## BYOK Carrier

```ts
await supafone.labs.telephony.configure({
  mode: "byok",
  provider: "twilio",
  credentials: {
    accountSid: process.env.TWILIO_ACCOUNT_SID!,
    authToken: process.env.TWILIO_AUTH_TOKEN!,
    fromNumber: "+14155550123"
  }
});
```

BYOK skips Supafone number rent but still keeps the hosted agent framework,
stages, tools, transcripts, recordings, account sync, and Supafone Supervisor
attached.
