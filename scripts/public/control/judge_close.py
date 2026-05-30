#!/usr/bin/env python3
"""judge_close.py — sanctioned JUDGE-lifecycle tick close (GP-241 #52
close-side). The symmetric companion to tick_close.py.

WHY THIS EXISTS (the multi-hour recurring failure, incl. by the
apparatus's own builder): there are TWO close lifecycles —
  * FORECAST-contract ticks  → `tick_close.py` (H4 needs an
    agent-side forecast outcome file).
  * JUDGE-adjudicated ticks (Lean-faithfulness, e.g. the BKM-DEVAC
    arc; daemon-minted contract) → NOT tick_close.py. The agent
    submits the close via `propose` with each frozen obligation
    witnessed `provenance:"judge:auto"`; the DAEMON emits a signed
    judge_request (the agent cannot steer the judge); the
    `ztare_judge` worker produces the verdict; the SAME close is
    re-submitted and resolves; the daemon stamps it.
There was a sanctioned wrapper for the first and NONE for the second,
and the distinction was documented nowhere — so the wrong tool
(tick_close.py) was used repeatedly and hit H4 forever. This wrapper
is the missing one. It is NOT daemon surgery — the daemon judge
mechanism is correct; this only removes the asymmetry + the footgun.

Re-judge on corrected work is AUTOMATIC: the judge_request id is
keyed on the witness sha (`_canon_wsha`, provenance dropped). A
strengthened/corrected witness ⇒ new sha ⇒ not `_already_judged` ⇒
fresh judge_request ⇒ re-validation. So after correcting a Lean
artifact, pass an updated witness and re-run; no special re-trigger.

Usage:
  python3 scripts/public/control/judge_close.py \
    --tick-row <TICK_ID> --contract-id <hex> --owner <o> \
    --witnesses-json '{"<obligation_item>":{"text":"...evidence..."}}'
  (provenance:"judge:auto" is injected into every witness; do NOT
   set it yourself.)  Re-run the IDENTICAL command after the worker
   has produced verdicts — that round resolves + stamps the close.

Protocol (fail-closed by design — read the daemon message, it IS
the contract): round 1 enumerates frozen obligations + emits
judge_requests; you owe a witness for EACH frozen obligation the
daemon names; re-run after verdicts to resolve.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PY = sys.executable


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tick-row", required=True,
                    help="the JUDGE tick id (NOT a forecast contract).")
    ap.add_argument("--contract-id", required=True,
                    help="the daemon-minted contract id from the "
                         "tick's signed start row.")
    ap.add_argument("--owner", default=os.environ.get("RD_OWNER", "agent:RD"))
    ap.add_argument("--witnesses-json", required=True,
                    help='{"<obligation_item>": {"text": "...the '
                         'evidence discharging this obligation..."}}. '
                         'provenance:"judge:auto" is injected for you.')
    ap.add_argument("--f-row-id", required=True,
                    help="the findings F-row id the daemon "
                         "materializes (reverse-H3) and semantically "
                         "gates (F6/#46) — it is daemon-VALIDATED, "
                         "not trusted-as-written.")
    ap.add_argument("--f-row-body", required=True,
                    help="the F-row markdown body (what was done / "
                         "result / honest scope). Daemon owns + "
                         "semantically validates it; a thin client "
                         "MUST submit it (fail-closed otherwise).")
    ap.add_argument("--goal", default="",
                    help="optional close text; the daemon recomputes "
                         "from the frozen start row anyway.")
    a = ap.parse_args()

    try:
        wmap = json.loads(a.witnesses_json)
        if not isinstance(wmap, dict) or not wmap:
            raise ValueError("must be a non-empty object")
    except Exception as e:
        print(f"🛑 JUDGE-CLOSE REFUSED — --witnesses-json must be a "
              f"non-empty JSON object {{item: {{...}}}}: {e}",
              file=sys.stderr)
        return 2

    # Inject the judge:auto provenance into EVERY obligation witness
    # (the daemon keys the judge_request on the provenance-stripped
    # witness sha; we must not let the caller forge a non-auto path).
    inj = {}
    for item, w in wmap.items():
        wd = dict(w) if isinstance(w, dict) else {"text": str(w)}
        wd["provenance"] = "judge:auto"
        inj[item] = wd

    close = {"tick_id": a.tick_row, "contract_id": a.contract_id,
             "f_row_id": a.f_row_id, "f_row_body": a.f_row_body}
    cmd = [PY, "-m", "src.ztare.gates.propose",
           "--type", "tick_close",
           "--text", a.goal or f"judge-close {a.tick_row}",
           "--close", json.dumps(close),
           "--witnesses", json.dumps(inj)]
    pr = subprocess.run(cmd, cwd=str(REPO), capture_output=True,
                         text=True, timeout=240)
    out = (pr.stdout or "") + (pr.stderr or "")
    sys.stdout.write(out if out.endswith("\n") else out + "\n")

    low = out.lower()
    # fail-loud: never let a non-official submission look closed.
    if any(s in low for s in (
            "observe_only", '"mode": "observe"', "dry-run",
            "dry_run", "quarantined", "local-enforce")):
        print("🛑 JUDGE-CLOSE: submission was NOT daemon-stamped "
              "(observe/dry-run/quarantine) — fail-closed, not "
              "laundering. Ensure ZTARE_OFFICIAL_STORE is the "
              "authoritative store and re-run.", file=sys.stderr)
        return 5
    if "official" in low and "judge:auto pending" not in low:
        print(f"\n✅ JUDGE-CLOSE STAMPED — {a.tick_row} closed "
              f"(verdicts present; daemon-stamped).")
        return 0
    if "judge:auto pending" in low or "re-submit" in low:
        print(f"\n⏳ JUDGE-CLOSE ROUND-1 OK — daemon emitted "
              f"judge_request(s) for {a.tick_row}. This round does "
              f"NOT close (by design). The out-of-loop ztare_judge "
              f"worker will produce verdict(s); then RE-RUN THIS "
              f"EXACT COMMAND to resolve + stamp the close. If the "
              f"daemon named frozen obligations with no witness "
              f"above, add a witness for EACH and re-run.")
        return 0
    # any other refusal: surface it verbatim (the message is the
    # contract); do not pretend success.
    print(f"\n🛑 JUDGE-CLOSE not stamped — read the daemon message "
          f"above (it enumerates exactly what is owed). Add the "
          f"missing per-obligation judge:auto witnesses and re-run. "
          f"Do NOT use tick_close.py for a judge tick (that is the "
          f"forecast-lifecycle wrapper; it hits H4 forever).",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
