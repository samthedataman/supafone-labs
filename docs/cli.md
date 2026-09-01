# `supafone` — the general CLI

`supafone` is a thin command-line wrapper over the public Python SDK
(`supafone_labs.client.Supafone`) and the REST contracts it speaks. Every
command is one SDK call, or — where a lifecycle genuinely needs more than one —
an explicitly sequenced set of calls whose partial outcome is reported rather
than hidden.

The package ships three console scripts and `supafone` does not replace either
of the others:

| Script | Scope |
| --- | --- |
| `supafone` | Account, hosted agents, managed numbers, QA, voices, campaigns |
| `supafone-campaign` | The versioned Campaign Platform control plane (compose → publish → dry-run → live) |
| `supafone-studio` | Studio Builder dedicated-stack provisioning |

```bash
pip install supafone-labs
supafone --help
```

## Authentication

`supafone` reads `SUPAFONE_API_KEY` by default, falling back to
`SUPAFONE_LABS_API_KEY`. An `sl_` key doubles as the account bearer token, so a
single credential reaches every lane.

```bash
export SUPAFONE_API_KEY=sl_live_...
supafone account show
```

Four sources are supported, in precedence order:

| Source | Safety |
| --- | --- |
| `--api-key <value>` | **Least safe** — visible in the process table and shell history. The CLI emits a warning whenever it is used. |
| `--api-key-file <path>` | Reads and strips the file's contents. |
| `--api-key-stdin` | Reads the key from stdin. |
| `SUPAFONE_API_KEY` / `SUPAFONE_LABS_API_KEY` | Default. |

```bash
supafone --api-key-file ~/.supafone/key capabilities
printf '%s' "$KEY" | supafone --api-key-stdin capabilities
```

Some surfaces need the **account lane** rather than an API key, and the SDK
resolves it from the environment:

* `SUPAFONE_TOKEN` — an account JWT, or
* `SUPAFONE_EMAIL` + `SUPAFONE_PASSWORD` — logged in lazily.

`campaign *` and `qa pstn-test` use the account lane. `qa twin` / `qa battle`
are session-scoped on the Labs cloud: with `SUPAFONE_EMAIL` and
`SUPAFONE_PASSWORD` set the CLI logs in first; without them it falls through on
the API key and warns that the Labs cloud may reject the run.

### Credentials are never printed

Output is redacted twice over:

1. Any **field** whose name is or ends in a credential word (`api_key`,
   `auth_token`, `password`, `secret`, `token`, `client_secret`, …) is masked to
   `abc***wxyz`. Identifier-shaped names are exempt, so `phone_number_sid`,
   `*_id`, `*_hash`, `*_ref`, and `*_url` stay readable.
2. Any credential **value** this process holds — the resolved API key,
   `SUPAFONE_TOKEN`, `SUPAFONE_PASSWORD` — is scrubbed from every rendered byte,
   including error messages echoed back by the API.

`supafone account show` performs no network call. It reports the resolved
endpoints plus a masked form and a 12-hex SHA-256 fingerprint of each
credential, so two machines can be compared without either printing a key.

## Output contract

`--output json` (the default) prints a **stable envelope** — the five keys are
always present, in every mode, on success and on failure:

```json
{
  "ok": true,
  "command": "numbers.buy",
  "data": { "number": { "id": "num_...", "simulated": false } },
  "error": null,
  "warnings": ["real carrier action: this was billable"]
}
```

On failure `data` is `null` (or, for a partial failure, the part that landed)
and `error` is populated:

```json
{
  "ok": false,
  "command": "agents.get",
  "data": null,
  "error": { "type": "api_error", "message": "Agent not found", "status": 404 },
  "warnings": []
}
```

Successful envelopes go to **stdout**; failed envelopes go to **stderr**, so
`supafone ... | jq` only ever sees results.

`--output text` renders the same envelope for humans:

```text
$ supafone --output text numbers list
ok  numbers.list
warning  simulated: no carrier action occurred and nothing was billed (Twilio is not configured for this account)
  numbers: (1)
    [0]
      id: num_2222
      phone_number: +14155550123
      simulated: true
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | The remote API returned an error (`error.status` carries the HTTP status) |
| `2` | Usage, local, or missing-confirmation error — **nothing was sent** |
| `3` | Partial failure — an earlier step landed; see `error.failed_step` and `error.remediation` |

## Global flags

| Flag | Default |
| --- | --- |
| `--base-url` | `SUPAFONE_API_BASE_URL` or `https://api.supafone.ai` |
| `--labs-base-url` | `SUPAFONE_LABS_API_BASE_URL` or `https://api.labs.supafone.ai` |
| `--agency-id` | `SUPAFONE_AGENCY_ID` |
| `--output` | `SUPAFONE_OUTPUT` or `json` |
| `--timeout` | `30.0` seconds |

## Confirmation flags

Irreversible or billable actions never proceed on a bare command. Confirmations
that name a target must match **exactly**, so a confirmation copied from one
run cannot authorize a different one.

| Command | Required flag |
| --- | --- |
| `agents create --with-number` | `--confirm-purchase` |
| `numbers buy` | `--confirm-purchase` |
| `numbers release <id>` | `--confirm "RELEASE NUMBER <id>"` |
| `agents delete <key>` | `--confirm "DELETE AGENT <key>"` |
| `qa pstn-test --to <number>` | `--confirm "AUTHORIZED PSTN TEST <number>"` |
| `campaign run` | `--confirm "LAUNCH"` |

## Account and capabilities

```bash
supafone account show       # local: redacted credentials + endpoints, no network
supafone account usage      # Labs GET /v1/usage
supafone account balance    # Labs GET /v1/billing/balance
supafone account checkout --sku sf_voice_minutes_400_v1
supafone capabilities       # GET /api/v1/labs/capabilities
```

The first five Supafone-managed runtime minutes are account-wide. They are not
reissued per key, agent, WebRTC tab, or CLI process. Calls reserve available
seconds atomically before provider startup, so concurrent calls cannot
overspend one balance; settlement refunds unused held seconds.

When a command receives a structured HTTP 402 with
`detail.code=managed_minutes_exhausted`, the CLI creates a server-authored
Stripe Checkout link and returns it under `data.payment`. It preserves the 402
in `error.status`; complete Checkout, then retry the original command.

`capabilities` is the provisioning contract: the agent fields the API accepts,
available runtimes (and which are PSTN-ready), managed vs. BYOK telephony
providers, industry presets, and the live voice catalog. Read it before
scripting agent creation — it is the source of truth for what this deployment
supports.

## Hosted agents

```bash
supafone agents create --name "Front desk" --industry dental
supafone agents create --name "Speed to lead" --direction outbound \
  --voice-provider ultravox --voice-id Mark \
  --set voice_watcher=true --set stage_count=5

supafone agents list --agent-type phone
supafone agents get agt_1234
supafone agents delete agt_1234 --confirm "DELETE AGENT agt_1234"
```

Agent config is one flat dict. First-class flags cover the common fields
(`--name`, `--assistant-name`, `--business-name`, `--industry`,
`--website-url`, `--goal`, `--greeting`, `--system-prompt`, `--language`,
`--preset-key`, `--agent-type`, and the `--voice-*` trio). Anything else in the
contract goes through `--config-file` (a JSON object) or repeated
`--set key=value`; values that parse as JSON are decoded, so
`--set voice_watcher=true` sets a boolean and `--set stage_count=5` an integer.

`--direction` selects the preset defaults: `inbound` (default) creates a phone
receptionist, `outbound` a campaign caller. Both default to Supafone-managed
telephony.

Deleting an agent does **not** release its numbers unless you ask:

```bash
supafone agents delete agt_1234 \
  --confirm "DELETE AGENT agt_1234" \
  --release-numbers
```

## Managed phone number lifecycle

Supafone-managed numbers move through four states. The API attaches a number to
an agent at purchase time — `numbers buy` therefore **requires** `--agent-key`.

Shared developer routes are a separate, operator-enrolled inventory. Inspect a
snapshot or follow realtime changes without exposing the account key in a
WebSocket URL:

```bash
supafone numbers pool
supafone numbers watch --events 10
```

The pool reports `available`, `in_use`, `cooldown`, `reserved`, and
`unavailable` states. It never treats customer-owned or merely unassigned
numbers as shared inventory.

```text
       search                buy (--agent-key)              unassign
available  ──────►  candidate  ──────────────►  assigned  ◄──────────►  owned, idle
                                                    │        assign         │
                                                    └──────────┬───────────-┘
                                                            release
                                                               ▼
                                                    returned to the carrier
```

```bash
# 1. Find candidates (no purchase, no charge)
supafone numbers search --area-code 415 --limit 5

# 2. Buy one and attach it to an agent (BILLABLE)
supafone numbers buy --agent-key agt_1234 \
  --phone-number +14155550123 --confirm-purchase

#    ...or let the search pick one
supafone numbers buy --agent-key agt_1234 --area-code 415 --confirm-purchase

# 3. Inventory
supafone numbers list --active-only

# 4. Move it between agents
supafone numbers unassign num_2222
supafone numbers assign num_2222 --agent-key agt_5678

# 5. Give it back to the carrier (IRREVERSIBLE)
supafone numbers release num_2222 --confirm "RELEASE NUMBER num_2222"
```

**`unassign` is not `release`.** `unassign` only detaches the number from its
agent — the account still owns it and is still billed for it, and the CLI says
so in `warnings`. `release` hands the number back to the carrier; it cannot be
reclaimed and the same digits may not be available again. `release` returns the
number to the Supafone pool by default; pass `--keep-out-of-pool` to suppress
that.

If the carrier refuses a release, the API fails the request without changing any
local assignment, so a failed `release` leaves the number assigned exactly as it
was.

## Partial failure behavior

Most commands are a single API call and are therefore all-or-nothing. Two are
not, and both report exactly what landed instead of collapsing into a generic
error:

* `agents create --with-number` — creates the agent, then buys its number.
* `campaign run` — validates the document, then hands it off with `launch=true`.

When the second step fails, the CLI exits **3** and writes a `partial_failure`
envelope naming the completed steps, the failed step, and the exact commands to
finish or undo the work. The first step is **not** rolled back automatically —
an agent that exists is a resource you may want to keep.

```json
{
  "ok": false,
  "command": "agents.create",
  "data": { "agent": { "agent_key": "agt_1234" }, "agent_key": "agt_1234" },
  "error": {
    "type": "partial_failure",
    "message": "the agent was created but buying its number failed: No numbers available to provision",
    "status": 502,
    "failed_step": "phone_number",
    "completed_steps": ["agent"],
    "remediation": "retry with `supafone numbers buy --agent-key agt_1234 --confirm-purchase`, or remove the agent with `supafone agents delete agt_1234 --confirm \"DELETE AGENT agt_1234\"`"
  },
  "warnings": []
}
```

Scripts should branch on the exit code, not on message text:

```bash
supafone agents create --name Desk --with-number --confirm-purchase
case $? in
  0) echo "agent + number ready" ;;
  3) echo "agent exists, number missing — see error.remediation" ;;
  *) echo "nothing was created" ;;
esac
```

`campaign run` fails **closed**: if the document does not validate for launch,
the CLI exits 2 and never calls apply, so no calls start.

## QA — free simulation vs. billable real audio

This is the distinction to keep straight. Three of the four QA commands cost
nothing at the carrier; one places a real phone call.

| Command | What runs | Carrier audio | Billing |
| --- | --- | --- | --- |
| `qa generate` | Scenario authoring from the agent's prompt | none | one Supervisor inference |
| `qa twin` | The generated suite played as **simulated** calls against the configured agent, judged pass/fail plus an SSR grade | none | Supervisor inferences only |
| `qa battle` | Every scenario played twice — once unsupervised, once with the Supervisor steering — for the supervision lift | none | Supervisor inferences only |
| `qa pstn-test` | **One real outbound PSTN call** through the account's calling provider | yes | a call credit + carrier minutes |

```bash
# Free — no phone network involved
supafone qa generate --agent-prompt-file prompt.txt --count 5
supafone qa twin --count 6 --turns 3 --supervised
supafone qa battle --scenario refund_bully --scenario angry_caller --turns 4
supafone qa history --agent intake --limit 10
```

`qa twin` and `qa battle` always carry the warning
`free simulation: scenarios ran against the agent without carrier audio`.

### Authorized PSTN tests

```bash
supafone qa pstn-test \
  --agent-id 7f3c... \
  --to +14155550123 \
  --confirm "AUTHORIZED PSTN TEST +14155550123"

supafone qa pstn-status <call_record_id>
```

The confirmation repeats the destination, so a confirmation string cannot
authorize a dial to a different number. Only place tests to numbers you own or
are explicitly authorized to call; the server additionally rate-limits these to
3 per minute and 10 per day per user and burns a call credit.

`qa pstn-test` returns `call_record_id` — feed it to `qa pstn-status` for the
call's status, transcript, classification, and watcher events.

### Reading `simulated`

Supafone degrades gracefully: with no Twilio credentials configured, number
searches, purchases, and test calls run against an in-memory simulation. Every
carrier-touching response carries a `simulated` flag, and the CLI promotes it
into `warnings` so a free simulated result is never mistaken for a billed one:

* `simulated: no carrier action occurred and nothing was billed (Twilio is not configured for this account)`
* `real carrier action: this was billable`
* `mixed simulated and real carrier results — check `simulated` per record`

## Voices

```bash
supafone voices list --provider cartesia --search calm --language en --limit 25
supafone voices preview Mark
```

`voices list` pages the normalized, provider-authorized catalog (Ultravox,
Cartesia, ElevenLabs, Inworld) with `--cursor` / `--limit`.

`voices preview` returns **metadata only** — the catalog record plus its
`preview_url` and the audio endpoint reference. No audio is downloaded and
nothing is billed:

```json
{
  "voice": { "id": "Mark", "provider": "ultravox", "language": "en", "...": "..." },
  "preview": {
    "preview_url": "https://.../mark.mp3",
    "endpoint": "GET https://api.supafone.ai/api/v1/labs/voices/preview?voice=Mark",
    "audio_downloaded": false
  }
}
```

Fetch the audio yourself from `preview_url`, or from the `endpoint` above with
your bearer token. A voice with no preview audio in the catalog is reported with
a warning rather than an error.

## Campaigns

```bash
# Draft a document from a description (no side effects)
supafone campaign generate "Win back lapsed patients" --csv-file leads.csv

# Validate it (no side effects)
supafone campaign validate campaign.yaml
supafone campaign validate campaign.yaml --assume-launch   # launch-time rules too

# Upsert the campaign WITHOUT starting calls
supafone campaign apply campaign.yaml

# Validate, then hand off to the campaign engine with launch=true (REAL CALLS)
supafone campaign run campaign.yaml --confirm "LAUNCH"

supafone campaign status <campaign_id>
```

`campaign run` is a handoff, not a runner: it validates for launch, applies the
document with `launch=true`, and returns a `handoff` block with the follow-up
commands. The campaign engine owns dialing from there.

For the **versioned** Campaign Platform — compose, revise, publish an immutable
version, reserve quota, dry-run, then launch a gated live run — use
`supafone-campaign`, which models that lifecycle with idempotency keys,
revisions, and digests. `supafone campaign` is the campaign-as-code surface for
the campaign engine and is deliberately the simpler of the two.

## Command index

```text
supafone account show|usage|balance
supafone capabilities
supafone agents create|list|get|delete
supafone numbers search|list|buy|assign|unassign|release
supafone qa generate|twin|battle|history|pstn-test|pstn-status
supafone voices list|preview
supafone campaign validate|generate|apply|run|status
```
