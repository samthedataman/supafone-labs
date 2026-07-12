# 🔑 API Keys and Auth

**One key does everything.** A single `sl_live_...` Labs key authenticates Labs
Cloud, the whole Supafone product API, the MCP server, and both SDKs — as long
as an app.supafone.ai account exists with the **same email** that owns the key.
Set `export SUPAFONE_TOKEN=sl_live_...` and you are done; there is no second key
to provision. Legacy scoped `sf_live_...` keys still work for hosted-agent-only
use, but they are the exception, not the default.

One key covers both surfaces:

| Key | Base URL | Used for |
| --- | --- | --- |
| `sl_live_...` | `https://api.labs.supafone.ai` **and** `https://api.supafone.ai` | Everything: Labs Cloud oracle, TTS, STT, logs, usage, builder, QA, optimizer — plus the whole product API (campaigns, calls, agents) via one-key auth |
| `sf_live_...` (legacy) | `https://api.supafone.ai/api/v1/labs` | Optional scoped key for hosted-agent-only use — the `sl_` key already covers this surface |

## One Key, Both APIs

An `sl_` key is no longer labs-only. The Supafone product API
(`https://api.supafone.ai`) accepts it as a bearer credential anywhere an
account JWT works: on first use it introspects the key against
`GET https://api.labs.supafone.ai/v1/keys/introspect`, maps the key's owner
email to your app.supafone.ai account, and caches the validated key
in-process for ~5 minutes. Anything doubtful — unknown key, deactivated key,
labs outage — fails closed as a 401, never a fallback.

```bash
export SUPAFONE_TOKEN=sl_live_...   # ONE env var: MCP + both SDKs, end to end

curl https://api.supafone.ai/api/v1/campaigns \
  -H "Authorization: Bearer $SUPAFONE_TOKEN"
```

Requirements:

- An app.supafone.ai account must exist with the **same email** that owns the
  key — otherwise the API answers 401 with "create an app.supafone.ai account
  with the same email".
- The key must be active in the labs console.

Account login (email/password or JWT) keeps working exactly as before — the
`sl_` path is additive.

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

## Legacy Scoped Hosted-Agent Keys

Your one `sl_` key already authenticates the hosted-agent API via one-key auth,
so most integrations never need a second key:

```bash
curl https://api.supafone.ai/api/v1/labs/capabilities \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"
```

For hosted-agent-only deployments you can still mint a scoped `sf_live_...` key
from the Supafone account-admin flow. It is the exception, not the default.

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
