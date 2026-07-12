# 💳 Admin Credit Provisioning

Admin credit provisioning is an internal Labs Cloud operation. It is protected
by `X-Admin-Secret` and should never be exposed to public clients.

```text
Base URL: https://api.labs.supafone.ai
Header:   X-Admin-Secret: <server-side-admin-secret>
```

## Create a Key

```bash
curl https://api.labs.supafone.ai/v1/keys \
  -X POST \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "plan": "developer",
    "grant_minutes": 60,
    "label": "launch"
  }'
```

Response:

```json
{
  "key": "sl_live_...",
  "plan": "developer",
  "minutes": 60
}
```

## Grant Minutes to a Key

```bash
curl https://api.labs.supafone.ai/v1/keys/grant \
  -X POST \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "sl_live_...",
    "minutes": 120,
    "plan": "growth"
  }'
```

## Grant Credits by Key or Email

`/v1/admin/credits/grant` is the account-aware grant endpoint. Provide either a
key or an email.

```bash
curl https://api.labs.supafone.ai/v1/admin/credits/grant \
  -X POST \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "minutes": 2500,
    "plan": "growth",
    "reason": "launch credit"
  }'
```

Behavior:

- If `key` exists and belongs to an account, credits land on the account.
- If `key` exists without an account, credits land on the key ledger.
- If `email` belongs to an account, credits land on that account and active
  keys inherit the plan.
- If `email` is new, a new `sl_live_...` key is created with the grant.

## List Keys and Accounts

```bash
curl https://api.labs.supafone.ai/v1/keys \
  -H "X-Admin-Secret: $ADMIN_SECRET"

curl https://api.labs.supafone.ai/v1/admin/accounts \
  -H "X-Admin-Secret: $ADMIN_SECRET"
```

Responses mask keys and include minutes remaining, plan, active status, source,
and account linkage.

## Deactivate a Key

```bash
curl https://api.labs.supafone.ai/v1/keys/sl_live_... \
  -X DELETE \
  -H "X-Admin-Secret: $ADMIN_SECRET"
```

## Security Rules

- Keep `ADMIN_SECRET` server-side only.
- Do not use unsigned Stripe webhooks outside local tests.
- Do not return raw key values from list endpoints.
- Log reasons for manual grants.
- Treat manual credits as financial state.
