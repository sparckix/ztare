#!/usr/bin/env python3
"""admin_retire_uncloseable_tick — the ONE liveness repair for a
jammed RD tick, now under Contract C4 (operator-IDENTITY boundary).

WHAT CHANGED (C4, forward spec): the prior gate was
`--i-am-operator` + env `ZTARE_OPERATOR_RETIRE=1` — both forgeable by
the agent's own runtime, and it wrote a local tombstone the daemon
never mediated. That entire path is **DELETED, not deprecated** (a
forgeable liveness hatch is the exact hole). This is now a thin
client: it builds the canonical payload, REQUIRES an ed25519
`operator_sig` over it from the PINNED operator key (which the agent
cannot read), and submits a daemon-mediated `tick_retire` transition.
No signature ⇒ no retire. The daemon writes the chain-valid signed
retire row; `tick_close_gate` consumes ONLY that (not a local json).

HONEST PRECONDITION (stated, not hidden): the signature is
unforgeable only where the agent process cannot read the operator key
and has no sudo path to the key-owning identity. That OS topology —
not this script — is what takes the capability away from the agent,
and it is C4's first-class not-the-builder acceptance criterion (the
deploy triad check). On a host where the agent can sudo, this gate is
decorative; there the retire must not be delegated to that host at
all (run it only where the topology holds).

USAGE (two steps, operator):
  1. Run with --owner/--tick-row/--reason and NO --operator-sig:
     prints the EXACT canonical payload + a fresh ts. Nothing is
     submitted.
  2. As the operator identity, sign that payload:
     `deploy/operator_sign.py '<payload>'`  → 64-ish hex.
     Re-run this script adding --ts <the ts> --operator-sig <hex>.
     It submits a `tick_retire` proposal; the daemon verifies the
     signature and materializes the signed retire (or quarantines).
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]

_REASONS = {
    "legacy_raw_propose_no_forecast_contract",
    "legacy_audit_finding_no_forecast_contract",
    "pre_lifecycle_bypass_debt",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", required=True)
    ap.add_argument("--tick-row", required=True,
                    help="the uncloseable F-row id (or unique substring)")
    ap.add_argument("--reason", required=True, choices=sorted(_REASONS))
    ap.add_argument("--ts", default="",
                    help="ISO8601 timestamp the operator_sig was "
                         "computed over (must match; ±1h freshness, "
                         "replay-kill). Omit in step 1.")
    ap.add_argument("--operator-sig", default="",
                    help="ed25519 hex over "
                         "f'{owner}|{tick_row}|{reason}|{ts}' by the "
                         "PINNED operator key. Omit in step 1.")
    a = ap.parse_args()

    if not a.operator_sig:
        ts = (a.ts or datetime.datetime.now(datetime.timezone.utc)
              .isoformat(timespec="seconds"))
        payload = f"{a.owner}|{a.tick_row}|{a.reason}|{ts}"
        print("=" * 70)
        print("C4 STEP 1 — NOTHING SUBMITTED. Sign this EXACT payload")
        print("as the operator identity (the agent cannot read the")
        print("operator key; that OS separation is the real gate):")
        print()
        print(f"  payload: {payload}")
        print()
        print("  deploy/operator_sign.py "
              f"{json.dumps(payload)}")
        print()
        print("Then re-run this command adding:")
        print(f"  --ts {ts} --operator-sig <hex-from-operator_sign>")
        print("=" * 70)
        # cold bc4qy8vsn: step-1 is NOT success — nothing submitted,
        # no sig. Exit NON-zero so no wrapper keying on rc can misread
        # "printed the payload" as "retire done" (C4 kill-test: no
        # operator_sig ⇒ refused).
        return 2

    if not a.ts:
        print("REFUSED: --operator-sig given but --ts missing. The "
              "signature is bound to the exact ts; pass the same ts "
              "you signed (step 1 printed it).", file=sys.stderr)
        return 2

    close = json.dumps({
        "owner": a.owner,
        "tick_row": a.tick_row,
        "reason": a.reason,
        "ts": a.ts,
        "operator_sig": a.operator_sig,
    })
    pr = subprocess.run(
        [sys.executable, "-m", "src.ztare.gates.propose",
         "--type", "tick_retire",
         "--text", f"operator retire {a.tick_row} ({a.reason})",
         "--goal", a.tick_row,
         "--close", close],
        cwd=str(REPO), capture_output=True, text=True, timeout=120)
    sys.stdout.write(pr.stdout)
    if pr.returncode != 0:
        sys.stderr.write(pr.stderr)
        print("\n🛑 RETIRE NOT STAMPED — the daemon refused (bad/"
              "absent operator_sig, stale ts, unprovisioned anchor, "
              "or bad reason). The tick is NOT retired; this gate is "
              "fail-closed by design.", file=sys.stderr)
        return 1
    print("\n=" * 1)
    print("OPERATOR-SIGNED RETIRE STAMPED (daemon-mediated, C4).")
    print("  NOT a valid RD tick_close. NOT creditable for "
          "micro_forecast / GP-230 / GP-233 / surfaced_consumption.")
    print("  tick_close_gate will read the CHAIN-VALID signed "
          "tick_retire (not a local file) and unblock with a DEBT "
          "BANNER.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
