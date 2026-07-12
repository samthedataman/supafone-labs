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
