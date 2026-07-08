# Troubleshooting

## 401 or Invalid Key

Check which API you are calling:

- `sl_live_...` works on `https://api.labs.supafone.ai`.
- `sf_live_...` works on `https://api.supafone.ai/api/v1/labs`.

Do not use an `sl_live_...` key for hosted-agent provisioning, and do not use an
`sf_live_...` key for Labs Cloud oracle/TTS/STT.

## 402 Out of Minutes

The Labs Cloud minute balance is empty.

```bash
curl https://api.labs.supafone.ai/v1/billing/balance \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"
```

Top up through the returned Stripe links.

## 429 Daily Cap Reached

Plans have request-count abuse caps on top of the minute balance. Check:

```bash
curl https://api.labs.supafone.ai/v1/usage \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"
```

## 503 Upstream Provider Not Configured

The gateway is missing the vendor key for the requested feature. Examples:

- oracle models need Anthropic, OpenAI, or xAI keys,
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

API-key-only auth is enough for usage, logs, oracle, TTS, STT, nudges, metrics,
and hosted-agent methods, but not for session-scoped builder flows.

## WebSocket Live STT Fails in Node

Node versions without a global `WebSocket` need an implementation:

```ts
import WebSocket from "ws";

supafone.liveTranscribe({ WebSocketImpl: WebSocket });
```

Browsers cannot set WebSocket headers, so the SDK sends the Labs key as an
`api_key` query parameter.

## Watcher Is Silent

Silence is valid when no correction is needed. If silence is unexpected, check:

- balance and daily caps,
- gateway provider configuration,
- whether transcripts are arriving,
- whether the confidence threshold filtered a weak directive,
- `/v1/logs` and `/v1/nudges` for recent events.
