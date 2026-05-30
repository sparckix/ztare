#!/usr/bin/env python3
"""pilot_to_residual_lever.py — Path A outcome → Path B governed loop.

Turns the proof-state pilot from a benchmark into the BUNDLED object:
every attempt (Path A agentic composer outcome) is routed through the
EXISTING kernel-wired residual_to_lever bridge (Path B), so each row
yields a typed residual_class + next_lever — the non-treadmill
invariant (no attempt dead-ends; nothing is 'retired_impossible' —
that class does not exist in ALLOWED_RESIDUAL).

Honest mapping (no laundering):
  stateful solved+clean -> CLOSED -> none_closed (UNVERIFIED until
    governance ratifies — two-scoreboard; a leak-tight kernel-clean
    solve is a CANDIDATE, never an auto-counted closure).
  not solved, timeout    -> apparatus_or_source_mismatch (a compute/
    search-budget limit, NOT a math gap — lever = more budget /
    stronger search / decompose; never 'theorem impossible').
  leak:self_name         -> gate_contract_not_crisp (closure not crisp).
  errs=N (real wrong proof)-> OPEN_GAP_REPORT -> theorem_or_pde_gap
    (genuine attempt, missing reasoning isolated — lever = the atom).

Task 2 (taxonomy): aggregates residual_class × gold-step band × arm +
the implied next_lever table = the residual taxonomy the bundled
harness needs to emit next_lever. Pure-Python on collected data;
machine-safe; does not touch the running hardened-30.
"""
from __future__ import annotations

import collections
import importlib.util as _u
import json
import sys
from pathlib import Path

_s = _u.spec_from_file_location(
    "rtl", str(Path(__file__).with_name("residual_to_lever.py")))
rtl = _u.module_from_spec(_s)
_s.loader.exec_module(rtl)


def _rec(row: dict, arm: str) -> dict:
    rid = f"{row['id']}::{arm}"
    solved = row[f"{arm}_solved"]
    why = (row.get(arm, {}) or {}).get("why", "") or ""
    if solved:
        return {"row_id": rid, "closure_verdict": "CLOSED",
                "target_kind": "proof_closure"}
    if why.startswith("timeout") or why.startswith("compile_fail:timeout"):
        return {"row_id": rid, "status": "harness_timeout_budget"}
    if why.startswith("leak:"):
        return {"row_id": rid, "v33_organ_flags": ["indirect_leak"]}
    if why.startswith("errs=") or "sorry=" in why:
        return {"row_id": rid, "closure_verdict": "OPEN_GAP_REPORT",
                "gap_report": {
                    "named_candidate_lemmas": [
                        (row.get("goal", "") or "")[:80] or "(goal)"],
                    "target_row": rid}}
    return {"row_id": rid, "status": f"harness_{why[:24] or 'unknown'}"}


def main() -> int:
    srcs = [p for p in ("/tmp/rung1/codex_pilot_ckpt.jsonl",
                         "/tmp/rung1/codex_pilot_hardened.jsonl")
            if Path(p).exists()]
    rows = []
    for p in srcs:
        for ln in Path(p).read_text().splitlines():
            try:
                d = json.loads(ln)
                d["_src"] = Path(p).name
                rows.append(d)
            except Exception:
                pass

    led = []
    by_class = collections.Counter()
    by_band_arm = collections.defaultdict(collections.Counter)
    lever_for = {}
    non_treadmill_ok = True
    for row in rows:
        gs = row.get("gold_steps") or 0
        band = ("2-4" if gs <= 4 else "5-8" if gs <= 8
                else "9-15" if gs <= 15 else "16+")
        for arm in ("stateful", "blind"):
            o = rtl.classify(_rec(row, arm))
            rc = o["residual_class"]
            assert rc in rtl.ALLOWED_RESIDUAL, rc
            if not o.get("next_lever"):
                non_treadmill_ok = False
            led.append({"id": row["id"], "src": row["_src"], "arm": arm,
                        "gold_steps": gs,
                        "solved": row[f"{arm}_solved"],
                        "why": (row.get(arm, {}) or {}).get("why"),
                        "residual_class": rc,
                        "next_lever": o["next_lever"],
                        "next_target": o["next_target_statement"][:140],
                        "scoreboard": o["scoreboard_note"]})
            by_class[(arm, rc)] += 1
            by_band_arm[arm][f"{band}|{rc}"] += 1
            lever_for[rc] = o["next_lever"]

    Path("/tmp/rung1/pilot_residual_ledger.jsonl").write_text(
        "\n".join(json.dumps(x) for x in led))

    print("=== (1) BUNDLED LOOP: every attempt -> typed residual + lever")
    print(f"rows={len(rows)}  attempts={len(led)}  "
          f"non_treadmill_invariant_holds={non_treadmill_ok}  "
          f"(no attempt dead-ends; 'retired_impossible' not in "
          f"ALLOWED_RESIDUAL by construction)")
    print("\nresidual_class distribution (arm, class -> count):")
    for (arm, rc), c in sorted(by_class.items()):
        print(f"  {arm:9s} {rc:30s} {c}")
    print("\n=== (2) RESIDUAL TAXONOMY -> next_lever the bundled harness "
          "must emit:")
    for rc, lev in sorted(lever_for.items()):
        print(f"  [{rc}]\n     -> {lev}")
    print("\nstateful failure structure by gold-step band:")
    for k, c in sorted(by_band_arm["stateful"].items()):
        print(f"  {k:48s} {c}")
    # two-scoreboard honesty: CLOSED rows are CANDIDATES, not closures
    cand = sum(1 for x in led if x["arm"] == "stateful"
               and x["solved"] and x["residual_class"] == "none_closed")
    print(f"\nTWO-SCOREBOARD: {cand} stateful kernel-clean CANDIDATES "
          f"-> none_closed -> route to governance ratification; "
          f"NOT auto-counted as closures.")
    print("ledger -> /tmp/rung1/pilot_residual_ledger.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
