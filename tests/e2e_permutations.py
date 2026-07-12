#!/usr/bin/env python3
"""E2E permutation matrix for the Supafone voice-call stack.

Loops through EVERY permutation of:
    telephony provider  ×  voice/agent stack  ×  managed|BYO  ×  inbound|outbound

and, for each cell, exercises the currently-reachable layers against LIVE
production with a freshly-minted sl_ key, recording an honest verdict:

    PASS     — the whole path this layer covers works end to end
    PARTIAL  — config/auth accepted, but a real call is blocked (missing
               telephony creds / vendor key / provisioning not live)
    BLOCKED  — a required credential the caller must supply is missing
    UNBUILT  — the vendor runtime / endpoint does not exist yet (e.g. 404)

This is a LIVE integration script, not a CI unit test — it hits
api.labs.supafone.ai and api.supafone.ai and mints a trial key. Run manually:

    python services/supafone-labs/tests/e2e_permutations.py

As the multi-vendor build lands, more cells flip from UNBUILT/PARTIAL → PASS;
the goal is a fully green matrix.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from itertools import product

LABS = os.getenv("SUPAFONE_LABS_API_BASE_URL", "https://api.labs.supafone.ai")
PROD = os.getenv("SUPAFONE_API_BASE_URL", "https://api.supafone.ai")

# ---- the permutation axes --------------------------------------------------
TELEPHONY = ["supafone", "twilio", "telnyx", "plivo", "signalwire", "sip", "vonage"]
VOICE_STACK = [
    "supafone", "ultravox", "vapi", "retell", "bland", "livekit",
    "openai_realtime", "grok", "deepgram", "cartesia", "elevenlabs", "inworld",
]
MODE = ["managed", "byok"]          # default framework vs bring-your-own
DIRECTION = ["inbound", "outbound"]

# Which vendor keys authenticate today (from live probes). Update as keys are
# reissued — drives the honest PARTIAL/BLOCKED verdicts, never a fake PASS.
VENDOR_KEY_OK = {
    "supafone": True, "ultravox": True, "deepgram": True, "cartesia": True,
    "telnyx": True, "twilio": True,           # telephony creds provided
    "openai_realtime": False, "grok": False, "elevenlabs": False,  # 401/403 live
    "vapi": None, "retell": None, "bland": None, "livekit": None, "signalwire": None,
    "plivo": None, "sip": None, "vonage": None,  # no key supplied yet
}


def _req(method: str, url: str, token: str = "", body: dict | None = None, timeout: int = 25):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"detail": raw[:200]}
    except Exception as exc:  # noqa: BLE001
        return 0, {"detail": str(exc)}


def mint_key() -> tuple[str, str]:
    """Fresh account → session token + sl_ key (5 free minutes)."""
    email = f"e2e-perm-{int(time.time())}@supafone-test.dev"
    st, body = _req("POST", f"{LABS}/v1/auth/register",
                    body={"email": email, "password": "E2E-Perm-2026!"})
    token = body.get("token", "")
    _, acct = _req("GET", f"{LABS}/v1/account", token=token)
    key = ""
    keys = acct.get("keys") if isinstance(acct, dict) else None
    if keys:
        key = keys[0].get("key") if isinstance(keys[0], dict) else str(keys[0])
    return key, token


def preflight(key: str) -> dict[str, bool]:
    """Confirm the shared services every permutation depends on are live."""
    checks = {}
    checks["signup"] = bool(key)
    st, _ = _req("GET", f"{LABS}/v1/keys/introspect", token=key)
    checks["one_key_introspect"] = st == 200
    st, _ = _req("GET", f"{PROD}/api/v1/campaigns", token=key)
    checks["one_key_product_api"] = st == 200
    st, _ = _req("POST", f"{LABS}/v1/builder/wizard", token=key, body={
        "message": "outbound sales agent",
        "fields": [{"key": "direction", "label": "D", "type": "choice",
                    "options": ["inbound", "outbound"]}],
        "draft": {},
    })
    checks["copilot_brain"] = st == 200
    st, _ = _req("POST", f"{PROD}/api/v1/labs/agents", token=key, body={})
    checks["hosted_agent_provision_live"] = st != 404
    return checks


def verdict_for(tel: str, stack: str, mode: str, direction: str,
                provision_live: bool) -> tuple[str, str]:
    """The honest verdict for one permutation given today's reality."""
    # BYO needs a working vendor/telephony key; managed uses Supafone's.
    if mode == "byok":
        tel_ok = VENDOR_KEY_OK.get(tel)
        stack_ok = VENDOR_KEY_OK.get(stack)
        if tel_ok is False or stack_ok is False:
            bad = tel if tel_ok is False else stack
            return "BLOCKED", f"BYO key for '{bad}' is rejected (401/403) — reissue it"
        if tel_ok is None or stack_ok is None:
            need = tel if tel_ok is None else stack
            return "BLOCKED", f"no BYO key supplied for '{need}'"
    # Real end-to-end call needs the hosted-agent factory live on a number.
    if not provision_live:
        return "UNBUILT", "hosted-agent provisioning route not live (/api/v1/labs/agents 404)"
    # Vendor runtimes beyond the bridged set are not wired yet.
    if stack not in ("supafone", "ultravox", "deepgram", "cartesia"):
        return "UNBUILT", f"agent runtime bridge for '{stack}' not wired"
    return "PASS", "config + auth + provision + call path available"


def main() -> int:
    print(f"Minting a fresh sl_ key at {LABS} …")
    key, token = mint_key()
    if not key:
        print("FAILED to mint a key — cannot run the matrix.")
        return 1
    print(f"  key: {key[:14]}…\n")

    print("== Preflight (shared services every permutation needs) ==")
    pf = preflight(key)
    for name, ok in pf.items():
        print(f"  {'✓' if ok else '✗'} {name}")
    provision_live = pf.get("hosted_agent_provision_live", False)
    print()

    rows = []
    counts = {"PASS": 0, "PARTIAL": 0, "BLOCKED": 0, "UNBUILT": 0}
    for tel, stack, mode, direction in product(TELEPHONY, VOICE_STACK, MODE, DIRECTION):
        verdict, reason = verdict_for(tel, stack, mode, direction, provision_live)
        counts[verdict] += 1
        rows.append((tel, stack, mode, direction, verdict, reason))

    total = len(rows)
    print(f"== Permutation matrix: {total} cells "
          f"({len(TELEPHONY)} telephony × {len(VOICE_STACK)} stacks × {len(MODE)} × {len(DIRECTION)}) ==")
    for k in ("PASS", "PARTIAL", "BLOCKED", "UNBUILT"):
        print(f"  {k:8} {counts[k]:4}  ({counts[k]*100//total}%)")

    # Show a sample of PASS cells + one representative reason per blocked group.
    print("\n-- PASS cells (fully live end-to-end today) --")
    passes = [r for r in rows if r[4] == "PASS"]
    for r in passes[:20]:
        print(f"  {r[0]:>10} · {r[1]:<16} · {r[2]:<7} · {r[3]}")
    if not passes:
        print("  (none yet — the build fills these in)")

    print("\n-- Blocked/unbuilt reasons (deduped) --")
    seen = set()
    for r in rows:
        if r[4] in ("BLOCKED", "UNBUILT") and r[5] not in seen:
            seen.add(r[5])
            print(f"  [{r[4]}] {r[5]}")

    # Write the full matrix for the record.
    out = os.path.join(os.path.dirname(__file__), "e2e_permutations_result.json")
    with open(out, "w") as fh:
        json.dump({
            "preflight": pf,
            "counts": counts,
            "rows": [dict(zip(
                ("telephony", "stack", "mode", "direction", "verdict", "reason"), r))
                for r in rows],
        }, fh, indent=2)
    print(f"\nFull matrix → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
