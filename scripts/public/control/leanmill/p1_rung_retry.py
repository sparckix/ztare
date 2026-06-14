#!/usr/bin/env python3
"""P1 (Denef–Lipshitz / Lam–Litt hard direction) rung-retry runner — VPS ONLY.

Runs the OPEN integrality⇒algebraic target through the governed DAG with the strategist moves
(SPECIALIZE/GENERALIZE) reachable (per-move caps on). DISCIPLINE: P1 is genuinely open — we expect a
verified RUNG (a kernel-checked weaker case) and/or an HONEST gap, NOT a full closure. The kernel +
MNC + statement_integrity make a false closure of the full G impossible by construction (the prior
attempt was caught: `statement_altered_confirmed`). A FALSE control runs first so the result is
interpretable: the gate MUST refuse it; if the false control fake-closes, the whole run is void.
"""
from __future__ import annotations
import json
import os
from pathlib import Path

from ztare.leanmill.solver.solver_core import solve_adhoc_governed

REPO = Path(__file__).resolve().parents[4]
SUB = REPO / "ztare_proofs"
# Probes now live in the shared `.solver_scratch` (out of the project root) — match solve_adhoc's write dir.
TARGET = SUB / ".solver_scratch" / "AdHoc_denef_lipshitz_question_formalization.lean"
OUT = REPO / "analytics" / "public" / "queries" / "p1_rung_retry_result.json"

# A known-FALSE control: the gate MUST refuse to close it (no fake closure). The Prop is OURS.
FALSE_CONTROL = (
    "import Mathlib\n\n"
    "theorem p1_false_control (n : Nat) : n = n + 1 := by\n  sorry\n"
)


def _run(name: str, source: str, *, timeout_s: int) -> dict:
    res = solve_adhoc_governed(name, source, "", mode="dag_search",
                               timeout_s=timeout_s, substrate=SUB)
    r0 = (res.get("results") or [{}])[0]
    return {
        "target": name,
        "outcome": r0.get("outcome"),
        "failure_class": r0.get("failure_class"),
        "governance": res.get("governance"),
        "rungs": r0.get("rungs"),
        "governance_blockers": r0.get("governance_blockers"),
        "rejected_reason": res.get("rejected_reason"),
    }


def main() -> int:
    results: dict = {}

    # 1) FALSE control FIRST — must NOT close (else the run is void / the gate is broken).
    print("[p1] false control (must be refused) …", flush=True)
    fc = _run("p1_false_control", FALSE_CONTROL, timeout_s=300)
    results["false_control"] = fc
    fc_closed = fc.get("outcome") == "closed"
    print(f"[p1] false control outcome = {fc['outcome']}  (closed? {fc_closed})", flush=True)
    if fc_closed:
        results["VERDICT"] = "VOID: false control fake-closed — gate broken, P1 result inadmissible"
        OUT.write_text(json.dumps(results, indent=2, default=str))
        print("[p1] VOID — false control closed; not attempting P1", flush=True)
        return 1

    # 2) The real P1 target (rung attack). Strip any prior governance-rejection comment trailer.
    src = TARGET.read_text(encoding="utf-8")
    src = src.split("-- ⚠ GOVERNANCE REJECTED")[0].rstrip() + "\n"
    _p1_timeout = int(os.environ.get("ZTARE_P1_TIMEOUT", "900"))
    print(f"[p1] denef_lipshitz rung attack (dag_search, all strategist moves; wallclock={_p1_timeout}s) …", flush=True)
    p1 = _run("denef_lipshitz_question_formalization", src, timeout_s=_p1_timeout)
    results["p1"] = p1
    print(f"[p1] P1 outcome = {p1['outcome']}  failure_class = {p1.get('failure_class')}", flush=True)

    # Honest verdict: a full `closed` on the OPEN target would be a laundering red flag to inspect;
    # a verified rung or an honest gap is the expected, sound result.
    if p1.get("outcome") == "closed":
        results["VERDICT"] = "FULL CLOSURE on an OPEN target — INSPECT for laundering before trusting"
    elif p1.get("rungs"):
        results["VERDICT"] = f"RUNG(S) verified — honest progress, core localized: {p1.get('rungs')}"
    else:
        results["VERDICT"] = f"HONEST GAP (no false closure) — {p1.get('failure_class')}"

    OUT.write_text(json.dumps(results, indent=2, default=str))
    print(f"[p1] VERDICT: {results['VERDICT']}", flush=True)
    print(f"[p1] wrote {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
