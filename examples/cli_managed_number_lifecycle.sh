#!/usr/bin/env bash
# The managed phone number lifecycle through the `supafone` CLI, end to end.
#
#   search -> buy (attached to an agent) -> unassign -> assign -> release
#
# Every command emits the stable JSON envelope, so this script branches on exit
# codes and reads fields with jq rather than scraping text.
#
#   0  success
#   1  the API returned an error
#   2  usage / confirmation error — nothing was sent
#   3  partial failure — an earlier step landed; error.remediation says what to do
#
# Requires: SUPAFONE_API_KEY (or --api-key-file / --api-key-stdin) and jq.

set -uo pipefail

AREA_CODE="${AREA_CODE:-415}"
AGENT_NAME="${AGENT_NAME:-CLI lifecycle demo}"

require() { command -v "$1" >/dev/null || { echo "need $1" >&2; exit 1; }; }
require supafone
require jq

# --------------------------------------------------------------------------
# 0. What does this deployment support, and whose key is this?
# --------------------------------------------------------------------------
# `account show` makes no network call and never prints the key itself — only a
# masked form and a fingerprint you can compare across machines.
supafone account show | jq '.data.credentials.api_key'
supafone capabilities | jq '.data.telephony, .data.runtimes.pstn'

# --------------------------------------------------------------------------
# 1. Create the agent that will own the number
# --------------------------------------------------------------------------
created=$(supafone agents create --name "$AGENT_NAME" --direction inbound) || {
  echo "agent creation failed" >&2
  exit 1
}
AGENT_KEY=$(jq -r '.data.agent.agent_key' <<<"$created")
echo "agent: $AGENT_KEY"

# --------------------------------------------------------------------------
# 2. Search — free. No purchase, no charge.
# --------------------------------------------------------------------------
# `simulated: true` means Twilio is not configured for this account and these
# are placeholder numbers: nothing below will reach a real carrier or bill.
search=$(supafone numbers search --area-code "$AREA_CODE" --limit 5)
jq -r '.warnings[]' <<<"$search"
jq -r '.data.numbers[] | "\(.phone_number)  \(.locality // "-")"' <<<"$search"
CANDIDATE=$(jq -r '.data.numbers[0].phone_number' <<<"$search")

# --------------------------------------------------------------------------
# 3. Buy — BILLABLE, and always attached to an agent
# --------------------------------------------------------------------------
# The API provisions a number onto an agent in one transaction, so --agent-key
# is required. --confirm-purchase is the CLI's acknowledgement of the charge.
bought=$(supafone numbers buy \
  --agent-key "$AGENT_KEY" \
  --phone-number "$CANDIDATE" \
  --confirm-purchase)
status=$?
if [ "$status" -ne 0 ]; then
  echo "purchase failed (exit $status)" >&2
  # The agent still exists — delete it or retry the purchase.
  exit "$status"
fi
NUMBER_ID=$(jq -r '.data.number.id' <<<"$bought")
jq -r '.warnings[]' <<<"$bought"   # "real carrier action: this was billable"

supafone numbers list --active-only | jq '.data.numbers'

# --------------------------------------------------------------------------
# 4. Move it between agents
# --------------------------------------------------------------------------
# unassign is NOT release: the account keeps (and is billed for) the number.
supafone numbers unassign "$NUMBER_ID" | jq -r '.warnings[]'
supafone numbers assign "$NUMBER_ID" --agent-key "$AGENT_KEY" | jq '.data.number.id'

# --------------------------------------------------------------------------
# 5. Optional: one authorized real-audio test call
# --------------------------------------------------------------------------
# This is the ONLY command here that dials the phone network. It is billable
# and rate-limited, the confirmation must repeat the destination exactly, and
# you must own or be authorized to call that number. The free equivalent is
# `supafone qa twin`, which plays the same agent as simulated calls.
if [ -n "${TEST_TO_NUMBER:-}" ] && [ -n "${TEST_AGENT_ID:-}" ]; then
  placed=$(supafone qa pstn-test \
    --agent-id "$TEST_AGENT_ID" \
    --to "$TEST_TO_NUMBER" \
    --confirm "AUTHORIZED PSTN TEST $TEST_TO_NUMBER")
  jq -r '.warnings[]' <<<"$placed"
  CALL_ID=$(jq -r '.data.call_record_id' <<<"$placed")
  supafone qa pstn-status "$CALL_ID" | jq '.data.call.status'
else
  # Free simulation — no carrier audio, nothing billed at the carrier.
  supafone qa twin --count 3 --turns 2 | jq -r '.warnings[]'
fi

# --------------------------------------------------------------------------
# 6. Release — IRREVERSIBLE
# --------------------------------------------------------------------------
# Hands the number back to the carrier; the digits may not be available again.
# The confirmation names the number id so a copied confirmation cannot release
# a different one. Returns to the Supafone pool unless --keep-out-of-pool.
supafone numbers release "$NUMBER_ID" \
  --confirm "RELEASE NUMBER $NUMBER_ID" | jq -r '.warnings[]'

supafone agents delete "$AGENT_KEY" --confirm "DELETE AGENT $AGENT_KEY" | jq '.data'
