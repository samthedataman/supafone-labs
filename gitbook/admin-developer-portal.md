# 🛠️ Admin Developer Portal

The admin portal is for Supafone operators, not ordinary SDK users. It requires
the private `ADMIN_SECRET` and should never expose raw API keys or provider
secrets.

## What Admins Should See

- total developer accounts,
- active and total API keys,
- remaining credited minutes,
- usage by endpoint,
- top developers by activity,
- recent logs,
- recent watcher nudges,
- recent call reports,
- account plans and active keys,
- masked API-key inventory,
- credit grants and plan changes.

## Developer Self-Service vs Admin

Developer self-service belongs in the public Console and Agent Builder:

- create more agents,
- see existing agents,
- search, buy, assign, return, or delete phone numbers,
- configure recording/transcription/artifacts,
- preview voices,
- stream logs,
- view recent calls, recordings, and transcripts.

Admin belongs in `admin.html`:

- issue keys,
- grant credits,
- inspect aggregate usage,
- audit developer activity,
- review self-healing watcher output across accounts.

## Private API Endpoints

The private Labs Cloud service exposes admin read surfaces:

```http
GET /v1/admin/overview?days=7
GET /v1/admin/activity?limit=100
GET /v1/admin/accounts
GET /v1/keys
POST /v1/keys
POST /v1/admin/credits/grant
```

All require `X-Admin-Secret`.

## Safety Rules

- Show masked API keys only.
- Do not show provider secrets.
- Use aggregate dashboards by default.
- Require explicit operator action for credits, plans, or key creation.
- Keep private service code out of public SDK pushes unless explicitly approved.
