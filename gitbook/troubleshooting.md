# Troubleshooting

## 401 or Invalid Key

One `sl_live_...` key authenticates **both** APIs — `https://api.labs.supafone.ai`
and `https://api.supafone.ai`. If you get a 401:

- Confirm the key is active in the Labs console.
- Confirm an app.supafone.ai account exists with the **same email** that owns
  the key — the product API maps the key to your account by owner email.

Legacy scoped `sf_live_...` keys authenticate only the hosted-agent surface
(`https://api.supafone.ai/api/v1/labs`), not Labs Cloud Supervisor/TTS/STT.

## 402 Managed Minutes Exhausted

The account-wide managed-runtime ledger cannot reserve another call. The first
five minutes belong to the account, so creating another key, agent, browser
session, or CLI process does not create another allowance. Calls already
starting or in progress may also hold `active_reserved_seconds`.

```bash
curl https://api.labs.supafone.ai/v1/billing/balance \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"
```

Read the structured response's `detail.code`. For
`managed_minutes_exhausted`, use its `checkout_endpoint` to create a Stripe
Checkout Session, open `checkout_url`, poll the Checkout status, and retry only
after payment is confirmed. See [Pricing and Credits](pricing-and-credits.md#structured-402-payment-flow).

## 403 Admin Secret Required

Admin endpoints require:

```text
X-Admin-Secret: <server-side-admin-secret>
```

Do not call admin endpoints from public browser clients.

## 429 Daily Cap Reached

Plans have request-count abuse caps on top of the minute balance. Check:

```bash
curl https://api.labs.supafone.ai/v1/usage \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"
```

## 503 Upstream Provider Not Configured

The gateway is missing the vendor key for the requested feature. Examples:

- BYOK Supervisor models need the selected provider key,
- TTS engines need the selected engine key,
- STT needs `DEEPGRAM_API_KEY`,
- Stripe webhooks need `STRIPE_WEBHOOK_SECRET` in production.

## Hosted Agent Created But No Number

Check whether you used `create()` instead of `createInboundWithNumber()` or
`createOutboundWithNumber()`. Creating an agent and buying/assigning a number
are separate operations unless you use the helper.

## Accidental Paid Number Risk

Default to:

```json
{ "number_strategy": "default_pool" }
```

Only use `dedicated` or `premium` after explicit user confirmation. Premium
numbers are `$3/month`.

## No Matching Number

Broaden the search:

```json
{
  "country_code": "US",
  "area_code": "415",
  "limit": 10
}
```

If the pool has no match, ask the user whether to search a nearby area code,
reserve a dedicated number, or bring their own carrier.

## Builder or QA Returns "Log In First"

Builder and QA run under a console session:

```ts
await supafone.login(process.env.SM_EMAIL!, process.env.SM_PASSWORD!);
```

API-key-only auth is enough for usage, logs, Supervisor, TTS, STT, nudges, metrics,
and hosted-agent methods, but not for session-scoped builder flows.

## WebSocket Live STT Fails in Node

Node versions without a global `WebSocket` need an implementation:

```ts
import WebSocket from "ws";

supafone.liveTranscribe({ WebSocketImpl: WebSocket });
```

Browsers cannot set WebSocket headers, so the SDK sends the Labs key as an
`api_key` query parameter.

## Supervisor Is Silent

Silence is valid when no correction is needed. If silence is unexpected, check:

- balance and daily caps,
- gateway provider configuration,
- whether transcripts are arriving,
- whether the confidence threshold filtered a weak directive,
- `/v1/logs` and `/v1/nudges` for recent events.
