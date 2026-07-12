# ☎️ Phone Numbers

Supafone-hosted agents support three Supafone-managed number strategies plus a
BYOK carrier path.

## Strategies

| Strategy | Monthly price | Behavior |
| --- | ---: | --- |
| `default_pool` | `$0` | Use an idle shared Supafone number for dev, demos, and early traffic. |
| `dedicated` | `$1.50` standard number-month | Reserve a standard number for an account or agent. |
| `premium` | `$3.00` premium number-month | Reserve a premium or easy number. |
| `byok` | `$0` Supafone number rent | Use customer-owned Twilio, Telnyx, Plivo, SIP, or similar credentials. |

The default strategy is `default_pool`. Dedicated and premium numbers are real
phone-number purchases or reservations and should require explicit user/admin
confirmation in product UI and automation.

## Search Shared Pool or Inventory

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

Use this only after the account has chosen a dedicated standard number.

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
stages, tools, transcripts, recordings, account sync, and Supafone Pro watcher
attached.
