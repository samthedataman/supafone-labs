# API Keys and Auth

Supafone Labs uses two key families. They are intentionally separate.

| Key | Base URL | Used for |
| --- | --- | --- |
| `sl_live_...` | `https://api.labs.supafone.ai` | Labs Cloud oracle, TTS, STT, logs, usage, builder, QA, optimizer |
| `sf_live_...` | `https://api.supafone.ai/api/v1/labs` | Hosted Supafone agent, phone number, voice, preset, and telephony API |

## Labs Cloud Auth

Create a trial key:

```bash
curl -X POST https://api.labs.supafone.ai/v1/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com"}'
```

Use it as a bearer token:

```bash
curl https://api.labs.supafone.ai/v1/usage \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"
```

The TypeScript SDK uses this key as `apiKey` for Labs Cloud methods:

```ts
const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY!,
});
```

## Hosted-Agent Auth

Hosted-agent API calls use a Supafone hosted-agent key that starts with
`sf_live_...`.

```bash
curl https://api.supafone.ai/api/v1/labs/capabilities \
  -H "Authorization: Bearer $SUPAFONE_API_KEY"
```

The hosted-agent API also accepts `x-supafone-key` and `x-supafone-api-key`, but
bearer auth is the recommended default.

In TypeScript, pass `supafoneApiKey` when the same SDK instance also talks to
Labs Cloud:

```ts
const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY!,
  supafoneApiKey: process.env.SUPAFONE_API_KEY!,
});
```

If you only use hosted-agent methods, this is enough:

```ts
const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_API_KEY!,
});
```

## Creating Hosted-Agent Keys

Hosted-agent key management is an account-admin operation on the Supafone app
API. It uses the normal app user session or JWT, not the hosted-agent key being
created.

```http
POST   /api/v1/labs/api-keys
GET    /api/v1/labs/api-keys?agency_id=...
DELETE /api/v1/labs/api-keys/{key_id}?agency_id=...
```

Create body:

```json
{
  "agency_id": "00000000-0000-0000-0000-000000000000",
  "name": "Production key",
  "scopes": [
    "agents:write",
    "agents:read",
    "voices:read",
    "calls:write",
    "numbers:read",
    "numbers:write",
    "telephony:read",
    "telephony:write"
  ]
}
```

The raw `sf_live_...` value is returned once. List and revoke responses should
only expose prefixes or metadata.

## Console Sessions

Labs Cloud also supports account sessions for console-scoped features:

```http
POST /v1/auth/register
POST /v1/auth/login
POST /v1/auth/key-login
GET  /v1/account
POST /v1/account/keys
PATCH /v1/account/keys/{key}
```

Builder and QA methods require a session token. Most read and usage endpoints
accept either a session token or an `sl_live_...` key.

## Key Hygiene

- Never commit `sl_live_...`, `sf_live_...`, provider keys, Twilio credentials,
  Stripe secrets, or admin secrets.
- Use environment variables in examples, tests, and deploys.
- Show only masked keys in dashboards and logs.
- Rotate keys when they leave the intended environment.

