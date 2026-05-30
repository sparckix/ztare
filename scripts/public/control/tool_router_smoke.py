#!/usr/bin/env python3
"""tool_router_smoke.py — §7-4 WIRING PROOF (NOT a benchmark).

The unbuilt lever: actually INVOKE the SOTA tactics already
in the pinned sandbox (Hammer/Duper/aesop/auto/exact?/simp_all) on a
live proof state through the persistent REPL, capture each result, and
route any closing proof through the ONE authoritative gate
(authoritative_axioms.govern → #print axioms). This proves the loop is
wired end-to-end; it does NOT claim closure throughput.

Cold-review Step-1 pass-gate (must all hold in the live run):
  - each tool call executes through the REPL and its result is captured
  - a closing tool's proof is governed (verdict carries axioms/persist)
  - ledger entries are run_id/source-tagged (NO foo/self-test pollution)
  - a tool that does NOT close is recorded as not-closed (no fake pass)

Modes:
  --self-test : machine-safe, NO Lean/codex (mock REPL). Isolated
                ledger (reuses authoritative_axioms.isolate_selftest_
                ledger) so it can NEVER pollute a real ledger.
  (default)   : LIVE — real PersistentLean on the pinned sandbox, one
                trivial target, one call per tool, governed. (Run only
                when a heavy-Lean slot is free; the trivial synthetic
                target is NOT a module file so Phase-B de-module is not
                even exercised — this smoke is independent of that fix.)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))

TOOLS = ["exact?", "simp_all", "norm_num", "aesop",
         "hammer", "duper", "auto"]
# §7-4 fix: hammer/duper/auto are in the sandbox oleans but NOT in the
# `import Mathlib` prelude ⇒ "unknown tactic". Open the tool-invocation
# context with these imports (sandbox's own V28ASmoke.lean shows
# `import Hammer; by hammer`). Scoped via PersistentLean(prelude=…) —
# NO global shared-prelude mutation (parity-control).
TOOL_PRELUDE = ("import Mathlib\nimport Hammer\nimport Duper\n"
                "import Auto\nopen scoped ENNReal NNReal BigOperators")
TARGET = "_trsmk"
DECL = f"theorem {TARGET} : (1 : Nat) + 1 = 2 := by sorry"


def _govern_closed(L, tool: str) -> dict:
    """A tool closed the goal in-REPL → ratify the composed proof
    through the ONE authoritative gate."""
    import authoritative_axioms as _AX
    # FIDELITY: govern's Phase-A elaborates the composed file by its OWN
    # imports. An import-less file ⇒ norm_num/aesop/hammer/duper are
    # "unknown tactic" ⇒ phaseA_errors (a harness artifact; the real
    # leak-tight wedge files carry their imports). Compose WITH imports
    # so the closure-ratification path is proven for the heavy tools.
    hdr = "import Mathlib\nimport Hammer\nimport Duper\nimport Auto\n\n"
    full = (hdr + f"theorem {TARGET} : (1 : Nat) + 1 = 2 := by\n"
            f"  {tool}\n")
    tline = hdr.count("\n") + 1
    return _AX.govern(L, full, tline, TARGET, 120, persist=False)


def run_live() -> int:
    import coherent_rung1 as cr
    from src.ztare.formal.lean_persistent import PersistentLean

    os.environ["ZTARE_GATE_RUN_ID"] = "toolrouter_smoke"
    os.environ["ZTARE_GATE_SOURCE"] = "smoke"
    print(f"[trs] warming REPL on {cr.SB.name} (Hammer/Duper/Auto "
          f"prelude) ...", flush=True)
    # Mathlib + Hammer + Duper + Auto >> the 180s default import budget
    # (trs2 died: "prelude load failed (timeout)"). 600s headroom.
    L = PersistentLean(cr.SB, prelude=TOOL_PRELUDE, import_timeout=600)
    op = L.start_tactic_proof(DECL, 180)
    if not op.get("ok"):
        print(f"FAIL-LOUD: could not open target: {op}", file=sys.stderr)
        return 2
    ps0 = op["ps"]
    rows = []
    for t in TOOLS:
        st = L.step(ps0, t, 60)             # invoke the tool in-REPL
        rec = {"tool": t, "in_goal": op.get("goal", "")[:120],
               "executed": ("err" in st),   # got a structured result
               "closed": bool(st.get("closed")),
               "err": (st.get("err") or "")[:160]}
        if st.get("closed"):
            g = _govern_closed(L, t)
            rec["gate_verdict"] = g.get("verdict")
            rec["gate_reason"] = g.get("reason")
            rec["axioms"] = g.get("axioms_deps")
        rows.append(rec)
        print(f"  {t:10s} closed={rec['closed']} "
              f"gate={rec.get('gate_verdict','-')} "
              f"err={rec['err'][:60]}", flush=True)
    L.close()
    Path("/tmp/rung1/_toolrouter_smoke.json").write_text(
        json.dumps(rows, indent=1))
    executed = sum(1 for r in rows if r["executed"] or r["closed"])
    closed = [r for r in rows if r["closed"]]
    ratified = [r for r in closed if r.get("gate_verdict") == "closure"]
    print("\n=== TOOL-ROUTER WIRING VERDICT ===")
    ok = (executed == len(TOOLS) and len(closed) >= 1
          and len(ratified) >= 1)
    print(json.dumps({
        "tools_executed_through_repl": f"{executed}/{len(TOOLS)}",
        "closed": [r["tool"] for r in closed],
        "closed_and_ratified_by_gate": [r["tool"] for r in ratified],
        "ledger_run_id": "toolrouter_smoke (tagged; no foo pollution)",
        "WIRING": "PROVEN" if ok else "INCOMPLETE — inspect rows"},
        indent=1))
    return 0 if ok else 1


def _self_test() -> int:
    import authoritative_axioms as _AX
    _AX.isolate_selftest_ledger()          # never touch a real ledger

    class _MockL:
        def start_tactic_proof(self, decl, t=180):
            return {"ok": True, "ps": 1, "goal": "⊢ 1 + 1 = 2"}

        def step(self, ps, tac, t=60):
            # simp_all/norm_num close; hammer executes but doesn't;
            # everything returns a STRUCTURED result (executed).
            closed = tac in ("simp_all", "norm_num", "exact?")
            return {"ok": True, "closed": closed, "ps": 2,
                    "goals": [], "err": "" if closed else "no progress"}

        def close(self):
            pass

        # govern() path mock: clean STD axioms -> closure
        def open_file(self, p, timeout=60):
            return {"ok": True, "errors": [], "sorries": [],
                    "messages": [{"data": "'_trsmk' depends on axioms: "
                                  "[propext]"}]}
    L = _MockL()
    op = L.start_tactic_proof(DECL)
    assert op["ok"]
    rows = []
    for t in TOOLS:
        st = L.step(op["ps"], t)
        rec = {"tool": t, "executed": ("err" in st),
               "closed": bool(st["closed"])}
        if st["closed"]:
            g = _govern_closed(L, t)
            rec["gate_verdict"] = g.get("verdict")
        rows.append(rec)
    executed = sum(1 for r in rows if r["executed"])
    closed = [r for r in rows if r["closed"]]
    ratified = [r for r in closed if r.get("gate_verdict") == "closure"]
    assert executed == len(TOOLS), ("all tools must return a "
                                    "structured result", rows)
    assert {r["tool"] for r in closed} == {"simp_all", "norm_num",
                                           "exact?"}, closed
    assert len(ratified) == len(closed), ("every closed proof must be "
                                          "governed to closure", rows)
    # non-closing tools recorded as not-closed (no fake pass)
    assert all(not r["closed"] for r in rows
               if r["tool"] in ("hammer", "duper", "auto", "aesop"))
    print("[self-test] tool_router_smoke: all 7 tools execute through "
          "(mock) REPL; closing tools governed→closure; non-closing "
          "recorded not-closed (no fake pass); ledger ISOLATED "
          "(isolate_selftest_ledger). NO Lean/codex.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    return _self_test() if a.self_test else run_live()


if __name__ == "__main__":
    raise SystemExit(main())
