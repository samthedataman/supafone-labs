# `supafone` — the general CLI

`supafone` is a thin command-line wrapper over the public Python SDK
(`supafone_labs.client.Supafone`) and the REST contracts it speaks. Every
command is one SDK call, or — where a lifecycle genuinely needs more than one —
an explicitly sequenced set of calls whose partial outcome is reported rather
than hidden.

## Install and verify

The public Python package installs the `supafone` command. Python **0.7.1**
adds the S2S and shared Agent Factory CLI controls:

```bash
python -m pip install --upgrade supafone-labs==0.7.1
supafone --version
supafone --help
```

`--version` prints the installed package version without credentials or a network
request. If the command is not on your shell's path, run
`python -m supafone_labs.cli --version` using the same Python environment.

The npm package remains `supafone-labs@0.7.0` and provides the TypeScript/JavaScript
SDK; it does not install a CLI executable. The public Python distribution does
not ship the separate internal `supafone-campaign` or `supafone-studio` commands.

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
   `SUPAFONE_TOKEN`, `SUPAFONE_PASSWORD`, and a selected Supervisor BYOK
   environment key (including `--supervisor-api-key-env`) — is scrubbed from every rendered byte,
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
| `--version` | Print the installed Python package version and exit |

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

## S2S Agent Factory

One hosted agent keeps its workflow and phone assignment when you change its
speaking model. Inspect the deployed catalog and provider configuration first:

```bash
supafone capabilities
supafone runtime get --provider openai
supafone runtime get --provider gemini
supafone runtime get --provider grok
supafone runtime get --provider hydra
```

`runtime get` reports masked configuration. `connected` means that a credential
resolves, not that a live provider session or phone call has succeeded. Supafone
uses its server-side platform key by default when configured; an account's
saved BYOK key takes priority. You need your Supafone key, not a vendor key in
`realtime`. To save an optional account override:

```bash
supafone runtime update --provider google --credentials-file ./google-key.json
```

The credentials file is a JSON object such as `{"api_key": "YOUR_PROVIDER_KEY"}`.
Use canonical IDs with `runtime update`: `ultravox`, `openai`, `google`, `xai`,
or `smallest`. Manage and protect this file like any other secret.

### Choose the speaking provider

```bash
# Default managed Ultravox, with its existing compatible voice configuration.
supafone agents create --name "Front desk" --industry dental \
  --s2s-provider ultravox --supervisor managed --stage-count 3

# Native S2S uses the speaking model's own voice.
supafone agents create --name "Realtime desk" --s2s-provider openai \
  --s2s-model gpt-realtime-2.1 --s2s-voice marin \
  --supervisor managed --manager managed --stage-count 3

# Change the saved selection for the agent's next call.
supafone agents update agt_1234 --s2s-provider gemini
supafone agents update agt_1234 --s2s-provider grok
supafone agents update agt_1234 --s2s-provider hydra

# Return to the managed Ultravox path; this sends realtime: null.
supafone agents update agt_1234 --s2s-provider ultravox
```

| Flag value | Speaking family | Saved provider ID |
| --- | --- | --- |
| `ultravox` | Ultravox and compatible custom TTS | `realtime: null` |
| `openai` | OpenAI | `openai` |
| `gemini` or `google` | Google Gemini | `google` |
| `grok` or `xai` | xAI Grok | `xai` |
| `hydra` or `smallest` | Smallest AI Hydra | `smallest` |

`--s2s-model` and `--s2s-voice` are optional; the server resolves omitted values
for the selected provider. Supply `--s2s-provider` or a `realtime.provider` in
`--config-file` when using either flag. Switching the config file to a different
provider clears its previous model and voice. The API validates supported IDs;
read `capabilities` instead of assuming every provider accepts the same values.

Updating the saved selection affects later sessions. It does not transfer an
active call, buy a number, or start audio. Optional native mid-call model routing
is a separate `runtime_routing` policy.

### Keep Ultravox custom TTS

Use the existing `--voice-provider`, `--voice-id`, and `--voice-model` controls
for compatible external TTS on Ultravox:

```bash
supafone voices list --runtime-provider ultravox --provider cartesia --configured-only
supafone agents update agt_1234 --s2s-provider ultravox \
  --voice-provider cartesia --voice-id CATALOG_VOICE_ID
```

Native OpenAI, Gemini, Grok and Hydra use `--s2s-voice`. An external TTS voice is
not a universal override for native S2S. Hydra accepts English and has no native
live transcript stream. See [voice output choices](voice-output-modes.md) and
[the native runtime contract](realtime-agent-factory.md) for provider limits.

### Supervisor and Manager

Both create and update accept `--supervisor` and `--manager`:

```bash
supafone agents update agt_1234 --supervisor managed --manager managed
supafone agents update agt_1234 --supervisor openai \
  --supervisor-api-key-env MY_SUPERVISOR_KEY --manager supervisor
supafone agents update agt_1234 --manager off --supervisor off
```

`--supervisor managed` uses the configured Supafone coaching profile. A BYOK
Supervisor accepts `anthropic`, `openai`, `gemini`, `openrouter`, `groq`, or
`cerebras`; it reads that provider's standard key environment variable or the
name given by `--supervisor-api-key-env`. `--supervisor-model` selects a BYOK
reasoning model. These keys belong to the reasoning model, independently of the
speaking provider.

`--manager managed` enables bounded Manager reasoning using platform keys;
`--manager supervisor` reuses the agent's Supervisor profile, including BYOK.
`--manager off` explicitly disables it. The Manager proposes permitted stage
transitions and consults specialists; server checks still enforce tools, gates,
and budgets. Specialists return advice rather than speaking in parallel or
executing business tools. Use a JSON config for detailed budgets and team roles.

### Generate and review stages

```bash
supafone agents plan --name "Booking desk" \
  --description "Capture the caller name, book a real slot, then confirm it." \
  --direction inbound --stage-count 3
supafone plans list
```

`agents plan` calls the hosted planner and returns its JSON envelope without
creating an agent or making a phone call. Review the returned stages before
placing the approved array in `call_stages`. `plans list` reads saved plans.
`--stage-count` accepts 3–8 on `agents create` and `agents plan`. To update an
existing agent's plan, submit an explicit `call_stages` array with
`agents update --config-file`; update does not accept `--stage-count`.

### Complete shared workflow config

Save this as `booking-agent.json`. It configures a three-stage plan, captured
facts, a bounded Manager, one specialist and explicit tool permissions:

```json
{
  "name": "Booking team",
  "description": "Capture the caller's details, book an approved slot, and confirm it.",
  "realtime": {"provider": "openai", "model": "gpt-realtime-2.1", "voice": "marin"},
  "telephony": {"mode": "supafone_managed", "provider": "supafone"},
  "capture_fields": ["name", "email"],
  "timezone": "America/New_York",
  "time_awareness": true,
  "tools": {"scheduling": true, "firm_knowledge": true},
  "supervisor": {"enabled": true, "mode": "managed"},
  "manager": {
    "enabled": true,
    "reasoning": "managed",
    "max_tasks": 6,
    "max_parallel": 2,
    "timeout_seconds": 6
  },
  "agent_team": {
    "enabled": true,
    "fallback_member_id": "scheduler",
    "members": [{
      "id": "scheduler",
      "instructions": "Use available evidence and never invent calendar availability.",
      "stage_keys": ["book"],
      "tools": ["check_availability", "book_appointment"]
    }]
  },
  "call_stages": [
    {
      "key": "capture",
      "name": "Capture",
      "goal": "Confirm and save the caller's name.",
      "tools": ["save_lead"],
      "requirements": {"required_fields": ["name"]},
      "next_stages": ["book"]
    },
    {
      "key": "book",
      "name": "Book",
      "goal": "Offer a real slot and book only with the caller's agreement.",
      "specialist_id": "scheduler",
      "tools": ["check_availability", "book_appointment"],
      "requirements": {"successful_tools": ["book_appointment"]},
      "next_stages": ["confirm"]
    },
    {
      "key": "confirm",
      "name": "Confirm",
      "goal": "Recap the successful booking and next steps.",
      "tools": [],
      "next_stages": []
    }
  ],
  "runtime_routing": {"enabled": false, "allowed_models": []},
  "recording": false
}
```

```bash
supafone agents create --config-file booking-agent.json
supafone agents readiness agt_1234
supafone agents get agt_1234
```

The calendar and selected tools must be connected on the server. An unsuccessful
booking cannot satisfy `successful_tools`; empty `tools` permits no business
tools in that stage, and empty `next_stages` marks a terminal stage. Shared
workflow controls require the corresponding hosted backend deployment; installing
the CLI does not deploy those services or configure missing provider keys.
[Shared runtime, Manager and teams](shared-agent-runtime.md) explains the limits.

For an existing agent, use `agents update --config-file` with a JSON object
containing only the fields to change, such as `call_stages`, `manager`, and
`agent_team`. Configure account telephony and provider keys through the
`telephony update` and `runtime update` commands; do not include those account
settings in an agent update.

Agent configuration is a top-level JSON object that can contain nested objects.
`--config-file` loads it, explicit flags overlay it, then repeatable `--set`
overrides top-level keys. `--set` decodes JSON values but does not expand dotted
paths. For example:

```bash
supafone agents update agt_1234 --set 'manager={"enabled":false}'
supafone agents update agt_1234 --set 'runtime_routing={"enabled":false,"allowed_models":[]}'
```

On create, `--direction inbound` (the default) selects receptionist defaults;
`--direction outbound` selects campaign defaults. Both default to managed
telephony. An ordinary update only sends the supplied fields.

```bash
supafone agents list --agent-type phone
supafone agents activate agt_1234
supafone agents pause agt_1234
supafone agents delete agt_1234 --confirm "DELETE AGENT agt_1234"
```

Deleting an agent retains its numbers unless you also pass `--release-numbers`.

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
supafone voices list --runtime-provider ultravox --model sonic-3 --configured-only
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

`supafone campaign` operates the campaign-as-code API. The separate internal
versioned Campaign Platform tooling is not included in this public package.

## Command index

Run `supafone <group> <command> --help` for that command's arguments. Global
flags such as `--agency-id` and `--output` precede the command group.

```text
supafone --version
supafone account show|usage|balance|checkout
supafone capabilities
supafone agents create|update|plan|list|get|readiness|activate|pause|delete
supafone tools list
supafone runtime get|update
supafone telephony get|update
supafone calls list|get|delete
supafone recordings list|get|delete
supafone transcripts list|get
supafone knowledge status|website-sync|website-detach|reindex|document-upload|document-delete|query
supafone activity list
supafone plans list
supafone numbers search|list|pool|watch|buy|assign|unassign|release
supafone qa generate|twin|battle|history|pstn-test|pstn-status
supafone voices list|preview
supafone campaign validate|generate|apply|run|status
```
