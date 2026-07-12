# 🚢 Deployment and Render

The live Labs deployment is split between the Python API and static web/docs
surface.

## Render Services

`render.yaml` defines:

| Service | Type | Domain | Root/publish path |
| --- | --- | --- | --- |
| `supafone-labs-api` | Python web service | `api.labs.supafone.ai` | `supafone-labs` |
| `supafone-labs-web` | Static web service | `labs.supafone.ai` | `supafone-labs/landing` |

API build and start:

```bash
pip install -e . -r cloud/requirements.txt
uvicorn cloud.app:app --host 0.0.0.0 --port $PORT
```

Health check:

```text
/healthz
```

The API has a persistent disk mounted at `/var/data` for its SQLite-backed
state.

## Important Boundaries

- Do not move `cloud/` without updating Render `rootDir`, build command, start
  command, and health path.
- Do not move `landing/` without updating the static publish path.
- Public SDK packages should not include private backend/admin/billing runtime
  files.
- Keep `.env` files, databases, provider keys, Stripe secrets, and Render
  operational state out of public releases.

## Required Environment

Common production variables include:

```text
ADMIN_SECRET
ANTHROPIC_API_KEY
OPENAI_API_KEY
XAI_API_KEY
DEEPGRAM_API_KEY
CARTESIA_API_KEY
ELEVENLABS_API_KEY
INWORLD_API_KEY
STRIPE_WEBHOOK_SECRET
STRIPE_SUBSCRIBE_URL
STRIPE_DEVELOPER_URL
STRIPE_GROWTH_URL
STRIPE_SCALE_URL
RESEND_API_KEY
FROM_EMAIL
DATA_DIR
```

Only set variables that the deployment actually uses. Never commit real values.

## Verification After Deploy

```bash
curl https://api.labs.supafone.ai/healthz
curl https://api.labs.supafone.ai/v1/pricing
curl https://api.labs.supafone.ai/v1/models
curl https://api.labs.supafone.ai/v1/voices
```

For hosted-agent API changes, also run:

```bash
cd supafone-labs
SUPAFONE_API_KEY=sf_live_... \
SUPAFONE_API_BASE_URL=https://api.supafone.ai \
npx tsx examples/smoke-hosted-agent.ts
```

## GitBook Replacement Notes

This GitBook source lives under `supafone-labs/gitbook/`. Publish that folder as
the GitBook root so `README.md` and `SUMMARY.md` drive navigation. The older
native docs can remain in place during migration until the GitBook publish path
is verified.
