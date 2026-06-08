#!/usr/bin/env python3
"""Materialize FAIR solver goals from sorried Lean source files.

The hard APN candidate files bundle the proof-construction DAG (helper defs AND
lemmas) in the SAME file as the statement, above a `theorem PN : ProblemPN := by
sorry`. Two naive paths both fail:
  - whole file  → LEAKS (hands the solver the proof construction);
  - target line → won't compile (`ProblemPN` and its statement vocabulary undefined).

A FAIR goal = the transitive DEFINITIONAL closure of the statement def
(`ProblemPN`) plus the target theorem with a `by` body — i.e. the problem
vocabulary the statement is phrased in, with every proof-introduced decl
(witnesses like `GammaP1_0`, helper lemmas) WITHHELD. The solver must reconstruct
the proof itself.

Boundary (principled, not lexical): start from the statement def's body, take the
closure of decls it references by name, transitively. Decls NOT reachable from the
statement are proof-only → dropped. Target theorem(s) themselves are never pulled
into the closure as dependencies.

Self-validating (the teeth): for each row, --validate
  (1) re-appends the file's ORIGINAL proof body for the target → must COMPILE
      against the extracted statement context (proves the statement is COMPLETE —
      we didn't drop a statement-defining decl); and
  (2) compiles the extracted goal with `:= by sorry` → must NOT be a clean close
      (proves we didn't trivialize it).
A row that fails either check is marked unfit, not emitted as fair.

Usage (run on the VPS, where the .lean files + toolchain live):
  materialize_statement_goals.py --slice <hard_slice.jsonl> --out <materialized.jsonl> [--validate] [--lean-root ztare_proofs]
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

# Substrate-generic statement/proof separation lives in the KERNEL
# (src/ztare/leanmill/solver/statement_extract.py) per the kernel/script
# boundary; this script owns only the CLI, slice I/O, and the Lean
# compile-validation orchestration below.
from ztare.leanmill.solver.statement_extract import build_goal  # noqa: E402,F401


def _validate(goal_full: str, lean_root: Path, timeout_s: int) -> dict:
    """Statement well-formedness: the extracted statement context + `:= by sorry`
    must TYPE-CHECK — i.e. compile with ONLY the `sorry` warning and NO error
    (the vocabulary the statement is phrased in is all present). An under-included
    closure would error `unknown identifier …` instead. We deliberately do NOT
    re-compile the published proof: it legitimately needs the withheld proof
    helpers, so a fair goal cannot be validated by it."""
    from ztare.gates.lean_compile_primitives import run_lake_compile_source, ensure_elan_on_path
    ensure_elan_on_path()
    sorry_src = f"import Mathlib\n\n{goal_full}\n  sorry\n"
    _ok, tail = run_lake_compile_source(sorry_src, lean_root, timeout_s=timeout_s)
    tail = tail or ""
    has_sorry = bool(re.search(r"uses [`'\"]?sorry|declaration uses", tail))
    has_error = bool(re.search(r"(?m)error:", tail))
    wellformed = has_sorry and not has_error
    return {
        "statement_typechecks": wellformed,
        "sorry_warning_present": has_sorry,
        "compile_error_present": has_error,
        "fit": wellformed,
        "compile_tail": tail[-300:],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--lean-root", default=str(REPO / "ztare_proofs"))
    ap.add_argument("--timeout", type=int, default=600)
    a = ap.parse_args()
    rows = [json.loads(l) for l in Path(a.slice).read_text().splitlines() if l.strip()]
    out_rows, fit, unfit = [], 0, 0
    for r in rows:
        sf = Path(r["source_file"])
        tgt = r.get("target_theorem_name")
        if not sf.exists():
            print(f"  {r['row_id']}: SKIP (source missing on this host: {sf})"); unfit += 1; continue
        built = build_goal(sf.read_text(encoding="utf-8"), tgt)
        if not built:
            print(f"  {r['row_id']}: SKIP (could not parse target {tgt})"); unfit += 1; continue
        rec = dict(r)
        rec["goal"] = built["goal"]
        rec["materialization"] = {"seeds": built["seeds"], "kept": built["n_kept"],
                                  "dropped_proof_decls": built["n_dropped"],
                                  "dropped_names": built["dropped_names"]}
        msg = (f"  {r['row_id']}: seeds={built['seeds']} kept={built['n_kept']} "
               f"dropped(proof)={built['n_dropped']}")
        if a.validate:
            v = _validate(built["goal"], Path(a.lean_root), a.timeout)
            rec["materialization"]["validation"] = v
            msg += (f" | typechecks={v['statement_typechecks']} "
                    f"err={v['compile_error_present']} FIT={v['fit']}")
            if not v["fit"]:
                unfit += 1; print(msg + "  <-- UNFIT, not emitted"); continue
        fit += 1
        out_rows.append(rec)
        print(msg)
    Path(a.out).write_text("\n".join(json.dumps(r) for r in out_rows) + "\n")
    print(f"\n[materialize] FIT={fit} unfit={unfit} -> {a.out}")
    print(f"[materialize] next: ZTARE_LEANMILL_APN_CORPUS=analytics/public/queries/lean/"
          f"apn_atlas_corpus.quarantined.json python {HERE/'orchestration_matrix.py'} "
          f"--slice {a.out} --providers native_hammer,claude_opus,codex_gpt5 --db <out.db>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
