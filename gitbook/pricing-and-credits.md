# 💰 Pricing and Credits

Labs Cloud uses a prepaid minute ledger. One Supafone minute covers hosted
agent runtime, self-healing watcher work, managed model/TTS/STT access, logs,
QA, and optimizer reports.

Pricing data is exposed publicly:

```bash
curl https://api.labs.supafone.ai/v1/pricing
```

## Plans

| Plan | Price | Included minutes | Overage | Included numbers |
| --- | ---: | ---: | ---: | ---: |
| Developer | `$49/mo` | `300` | `$0.14/min` | `0` |
| Growth | `$249/mo` | `2,500` | `$0.11/min` | `3` |
| Scale | `$999/mo` | `12,000` | `$0.085/min` | `20` |

The trial signup grants 5 free minutes.

## What a recording costs

Supafone does **not** add a second fee just because a call is recorded. Hosted
calls debit the connected voice-agent runtime from the minute ledger. The
recording artifact is included. Transcription, supervisor/SecondMind work, QA,
and longer-term storage remain separate internal meters so usage and margins
stay auditable; the customer still sees one clear Supafone balance.

## Usage Meters

| Meter | Unit | Notes |
| --- | --- | --- |
| `agent_minute` | minute | Live hosted voice-agent runtime |
| `self_healing` | second | Oracle, QA, optimizer, and whisper work |
| `tts` | spoken second | Hosted voice output |
| `stt` | audio second | Prerecorded and live transcription |
| `shared_number_pool` | pooled route | Default shared Supafone number pool |
| `managed_number` | number-month | Dedicated Supafone-managed phone number |
| `premium_number` | number-month | `$3/month` premium number |

## Balance

```bash
curl https://api.labs.supafone.ai/v1/billing/balance \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"
```

Response shape:

```json
{
  "plan": "growth",
  "seconds_remaining": 150000,
  "minutes_remaining": 2500,
  "top_up": {
    "developer": "https://...",
    "growth": "https://...",
    "scale": "https://...",
    "pricing": "/v1/pricing"
  }
}
```

## Hosted Stripe Checkout

The SDK and MCP create Checkout Sessions on the server, so a secret Stripe key
never enters a client application or model context:

```python
checkout = client.labs.billing.checkout(
    kind="plan",
    plan_key="growth",
)
print(checkout["checkout_url"])
```

After payment, poll `client.labs.billing.status(checkout_session_id)`. Use
`client.labs.billing.portal()` to return an authenticated Stripe Customer Portal
link for payment methods, invoices, and cancellation. Stripe webhook events are
signature-verified and deduplicated before credits or entitlements are granted.

## Stripe Checkout Metadata

Stripe grants are controlled by checkout metadata:

```json
{
  "plan_key": "developer",
  "included_minutes": "300",
  "credits_minutes": "400"
}
```

Rules:

- `plan_key` supports `developer`, `growth`, and `scale`.
- Subscription checkout grants `included_minutes`, or the plan default.
- One-time credit packs use `credits_minutes` when present.
- `invoice.paid` renewals grant the subscription minutes again.
- If an account exists for the email, credits land on the account balance.
- Otherwise credits land on the newest active key, or a new `sl_live_...` key is
  issued.

## Number Billing

The safe default is the shared pool:

```json
{
  "default_strategy": "default_pool",
  "default_pool_price_monthly": 0
}
```

Dedicated and premium numbers are paid number-month choices:

```json
{
  "dedicated_number_price_monthly": 1.5,
  "premium_number_price_monthly": 3
}
```

Product flows should make number purchases explicit. Do not silently upgrade a
shared-pool user to a dedicated or premium number.

For SDK and MCP callers, the first paid-number request returns a hosted
`checkout_url`. After Stripe reports `paid`, repeat the purchase with the
`billing_checkout_session_id`. Supafone claims the single-use entitlement,
provisions the carrier number, then consumes the entitlement. A retry returns
the already-provisioned number rather than buying another one.
