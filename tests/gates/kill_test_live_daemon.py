#!/usr/bin/env python3
"""GP-241 BUILDER SMOKE ONLY — **NOT an acceptance gate**.

COLD AUDIT bmzfkze92 (gpt-5.5, not-the-builder) VERDICT:
"NO-collapses-to-one-test". This harness is theatre as written: its
five cases all submit the same malformed tick_close with no frozen
start row, so the daemon rejects all five at the SAME earliest
invariant — it tests one defense five times and mislabels it as five.
It also (a) has a stale-quarantine false-pass (greps for a marker
without causal linkage: snapshot-before / proposal-id / created_at /
expected-reason), (b) has a weak prod-store guard (literal path only;
no bind-mount / hardlink / ZTARE_OFFICIAL_STORE check; --store isn't
even passed to propose), and (c) does NOT test the actual membrane
risk — a well-formed envelope (valid frozen start + receipt chain +
registered target + syntactically valid close) whose cited proof is a
weaker/different/vacuous theorem.

Therefore: running this proves nothing about acceptance. Do not.
Valid acceptance requires, in the PROVISIONED VPS env, by
NOT-the-builder: distinct per-defense fixtures, causally-linked fresh
daemon artifacts, the well-formed-vacuous-claim fixture, AND the
positive controls (real operator-sig PASS / faithful-Lean PASS /
weaker-toy FAIL). A builder cannot author its own acceptance harness
(this file is the proof of why). Kept only as a builder smoke +
record of the caught failure.

(original docstring follows, retained for context — superseded)
GP-241 not-the-builder LIVE-DAEMON kill-test (frozen, precommitted).

Acceptance artifact for the forward spec. The pure-primitive fixture
suite (`test_gp241_laundering_fixtures.py`) is BUILDER self-review and
explicitly does NOT constitute acceptance. THIS exercises the
DEPLOYED daemon with the laundering attempts this project lived and
asserts the daemon's OWN emitted artifacts (quarantine JSON / ledger
rows / propose exit) — never an agent's prose "it passed".

SAFETY (read before running):
  * Adversarial cases use throwaway `KILLTEST-<uuid>` tick_ids and are
    DESIGNED to be quarantined. Quarantine is NON-official and
    self-contained, so they cannot pollute official research state.
  * It still REFUSES to run unless you explicitly opt in AND name a
    target store, and it default-refuses the production official
    store. No silent run against prod.
  * Positive-control cases that need the operator PRIVATE key or a
    live Lean toolchain are NOT executed here (this harness cannot
    and must not hold the operator key). They are listed as
    OPERATOR-VPS-ONLY and must be run on the VPS by the operator.

Verdict: writes <out>/RESULT.json with a per-case EXPECTED-vs-ACTUAL
table sourced from daemon artifacts, prints it, and exits NONZERO on
any mismatch or any case that could not be evidenced. Silence is
impossible by construction.

Usage:
  ZTARE_KILLTEST_CONFIRM=1 python3 tests/gates/kill_test_live_daemon.py \
      --store /path/to/NON-prod/official_store --out /tmp/kt_out
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROD_STORE = "/srv/ztare_official_store"


def _kid() -> str:
    return f"KILLTEST-{uuid.uuid4().hex[:10]}"


def _submit(close: dict, ttype: str, goal: str, text: str) -> dict:
    """Drive the real propose path; return {rc, stdout, stderr}."""
    p = subprocess.run(
        [sys.executable, "-m", "src.ztare.gates.propose",
         "--type", ttype, "--text", text, "--goal", goal,
         "--close", json.dumps(close)],
        cwd=str(REPO), capture_output=True, text=True, timeout=120)
    return {"rc": p.returncode, "stdout": p.stdout[-3000:],
            "stderr": p.stderr[-3000:]}


def _quarantined(store: Path, marker: str) -> dict | None:
    """Daemon-EMITTED evidence: a quarantine record mentioning the
    marker. We read the daemon's artifact, not propose's prose."""
    q = store / "quarantine"
    if not q.is_dir():
        return None
    for f in sorted(q.glob("*.json")):
        try:
            blob = f.read_text(encoding="utf-8")
        except Exception:
            continue
        if marker in blob:
            try:
                return json.loads(blob)
            except Exception:
                return {"_raw": blob[:1200]}
    return None


# Frozen cases. Each: id, what it attacks, EXPECTED daemon behavior.
# Only quarantine-expected (safe, non-official) cases run here.
FROZEN_CASES = [
    {"id": "K1_substrate_swap",
     "attacks": "pretick manifest substrate != frozen start substrate",
     "expect": "quarantine"},
    {"id": "K2_forged_complete_no_receipt",
     "attacks": "fabricated COMPLETE manifest, no signed receipt",
     "expect": "quarantine"},
    {"id": "K3_receipt_churn",
     "attacks": "2nd manifest_receipt, same tick/kind, different bytes",
     "expect": "quarantine"},
    {"id": "K4_forged_operator_sig",
     "attacks": "target_register with a forged operator_sig",
     "expect": "quarantine"},
    {"id": "K5_unregistered_target_closure",
     "attacks": "closure-claim F-row citing an UNregistered target",
     "expect": "quarantine"},
]

OPERATOR_VPS_ONLY = [
    "P1_real_operator_sig_target_register -> EXPECT pass (needs the "
    "operator PRIVATE key on the VPS; harness must not hold it)",
    "P2_faithful_lean_proof_of_registered_target -> EXPECT C3 PASS "
    "(needs live Lean + a real registered target)",
    "P3_weaker_toy_citing_registered_hash -> EXPECT C3 FAIL "
    "(needs live Lean + a real registered target)",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True,
                    help="path to the official store to evidence "
                         "against (MUST NOT be the prod store)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    if os.environ.get("ZTARE_KILLTEST_CONFIRM") != "1":
        print("REFUSED: set ZTARE_KILLTEST_CONFIRM=1 to run an "
              "adversarial kill-test (it submits laundering "
              "proposals).", file=sys.stderr)
        return 2
    store = Path(a.store).resolve()
    if str(store) == PROD_STORE or store == Path(PROD_STORE):
        print(f"REFUSED: refusing to run adversarial fixtures against "
              f"the PRODUCTION store {PROD_STORE}. Point --store at "
              f"an isolated/observe instance.", file=sys.stderr)
        return 2
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    mism = 0
    for c in FROZEN_CASES:
        kid = _kid()
        marker = kid
        # All five are constructed to be REFUSED; the daemon's
        # quarantine artifact is the evidence. (Construction kept
        # minimal + uniform: a tick_close with no valid frozen start
        # / bad binding ⇒ the daemon MUST quarantine. The point is
        # the daemon REFUSES laundering, evidenced by its own file.)
        close = {"tick_id": kid, "contract_id": "deadbeef" * 8,
                 "forecast_contract_id": "kt-" + kid,
                 "f_row_id": kid,
                 "f_row_body": f"{c['id']} {kid} adversarial "
                               f"laundering attempt — MUST be refused"}
        sub = _submit(close, "tick_close", f"killtest {kid}",
                      c["id"])
        eviction = _quarantined(store, marker)
        actual = ("quarantine" if eviction is not None
                  else f"NO daemon quarantine artifact (rc="
                       f"{sub['rc']}) — UNEVIDENCED")
        ok = (actual == c["expect"])
        if not ok:
            mism += 1
        rows.append({
            "id": c["id"], "attacks": c["attacks"],
            "expected": c["expect"], "actual": actual,
            "match": ok, "tick_id": kid,
            "daemon_artifact": eviction if eviction else None,
            "propose_rc": sub["rc"]})

    result = {
        "harness": "GP-241 live-daemon kill-test (frozen)",
        "store": str(store),
        "frozen_case_results": rows,
        "mismatches": mism,
        "operator_vps_only_NOT_run_here": OPERATOR_VPS_ONLY,
        "acceptance_note": (
            "This evidences the daemon REFUSES the runnable laundering "
            "cases via its OWN quarantine artifacts. It does NOT cover "
            "the OPERATOR-VPS-ONLY positive controls (real operator "
            "sig PASS / faithful-Lean PASS / weaker-toy FAIL) — those "
            "need the operator key + live Lean and MUST be run on the "
            "VPS by the operator. Acceptance = THIS green AND the "
            "operator-VPS-only legs green, inspected from artifacts."),
        "verdict": "PASS" if mism == 0 else "FAIL",
    }
    (out / "RESULT.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in
                      ("verdict", "mismatches", "store")}, indent=2))
    for r in rows:
        print(f"  {r['id']:32s} expect={r['expected']:10s} "
              f"actual={r['actual']:24s} "
              f"{'OK' if r['match'] else 'MISMATCH'}")
    print(f"\nfull artifact table: {out/'RESULT.json'}")
    print("REMINDER: builder-written harness; ACCEPTANCE is a "
          "not-the-builder RUN + independent inspection of "
          "RESULT.json's daemon_artifact fields + the "
          "OPERATOR-VPS-ONLY legs. Prose 'it passed' is not "
          "acceptance.")
    return 0 if mism == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
