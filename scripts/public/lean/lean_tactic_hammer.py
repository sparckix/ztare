#!/usr/bin/env python3
"""Lean tactic hammer — try exact?/aesop/polyrith/linarith/omega BEFORE the LLM.

The genuine 10x bet of 2026-05-06: Lean already has trained tactic search
(`exact?`, `aesop`, `polyrith`, `linarith`, `omega`, `decide`, `simp`).
The typed-endpoint pack format IS exactly what these tools want as
context. Run them BEFORE the LLM — if any succeed, we have a verified
patch with zero API tokens.

# Why this is the genuine 10x

  - Eliminates a whole class of LLM failures that Lean already solves
  - Zero LLM cost on cases Lean handles natively
  - Frees revision-loop API budget for the genuinely hard cases
  - Tactics are TRAINED on real proofs (Mathlib4 corpus); LLMs are not

# Pipeline

  1. Take a (target, field, patch_class) triple from typed_endpoint_pack
  2. Synthesize a target theorem statement using the patch class shape
  3. For each tactic in {exact?, aesop, polyrith, linarith, omega, decide,
     simp_all, norm_num, ring, rfl}:
       a. Write a Lean file with the statement + tactic
       b. lake build it
       c. If green: report tactic + the proof it found (if any)
       d. If red: try next tactic
  4. Report (tactic_succeeded | None, proof_text | None)

# Wiring into typed_endpoint_pack

  The endpoint pack runner can call this BEFORE invoking the LLM. If a
  hammer succeeds, log as a "hammer_verified" success and skip LLM
  entirely. If all hammers fail, the failed-tactic list goes into the
  LLM prompt as a hint ("Lean's exact?, aesop, polyrith, ... already
  tried and could not discharge this; you need a non-trivial step").

# Honest scope

  - Synthesizing the theorem statement requires field-type elaboration
    we don't fully have. Fallback: use the LLM ONCE to produce just the
    SIGNATURE (no proof), then run hammers on the signature.
  - `exact?` returns "Try this: <proof>" in stdout; we capture and
    record but verifying the suggestion separately would be cleaner.
  - Some tactics (polyrith) require external Sage; gracefully skip if
    unavailable.

Usage:
    python scripts/public/lean/lean_tactic_hammer.py \\
        --target TrackBProfileLipschitzClayObligation \\
        --field continuation \\
        --patch-class instance_with_evidence
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

# Ordered by likelihood of cheap success. `exact?` first (returns proof
# from Mathlib's premise database). `aesop` second (general-purpose).
# Then domain-specific.
HAMMER_TACTICS = [
    ("rfl",       "exact rfl"),
    ("decide",    "decide"),
    ("exact_q",   "exact?"),
    ("aesop",     "aesop"),
    ("simp_all",  "simp_all"),
    ("norm_num",  "norm_num"),
    ("linarith",  "linarith"),
    ("omega",     "omega"),
    ("ring",      "ring"),
    ("polyrith",  "polyrith"),
]


def synthesize_statement(target: str, field: str, patch_class: str,
                          field_type: str | None) -> str:
    """Produce a tactic-block-ready Lean theorem header for the target.

    Substrate-agnostic best-effort: we produce a vacuous header for the
    field if no patch-specific shape is known. The hammer will reject
    almost everything but `rfl` / `decide` on truly trivial cases —
    which is fine; the test is whether ANY case is trivially closable.

    Real wiring should pass the LLM-produced signature through; this
    is the standalone smoke test.
    """
    target_safe = re.sub(r"[^A-Za-z0-9_]", "_", target).lower()[:30]
    field_safe = re.sub(r"[^A-Za-z0-9_]", "_", field).lower()[:30]
    name = f"hammer_attempt_{target_safe}_{field_safe}"
    if patch_class == "instance_with_evidence" and field_type:
        # Try to construct an instance: `noncomputable def n (k : T) : Target := ⟨k⟩`
        return (
            f"noncomputable def {name} (k : {field_type}) : "
            f"{target} := ⟨k⟩"
        )
    if patch_class == "transitivity_adapter":
        # Trivial "x ≤ x" placeholder — only `rfl` / `le_refl` should close it
        return f"theorem {name} (x : ℝ) : x ≤ x := by"
    if patch_class == "branch_wise_falsifier":
        return f"theorem {name} : True := by"
    if patch_class == "source_provenance_bridge":
        return f"theorem {name} (x : ℝ) : x = x := by"
    return f"theorem {name} : True := by"


def build_lean_file(statement: str, tactic_block: str,
                     imports: list[str] | None = None,
                     open_namespaces: list[str] | None = None) -> str:
    imports = imports or [
        "import Mathlib.Tactic",
        "import ZtareProofs.ns_phase_latency_clay_bridge",
    ]
    opens = [f"open {ns}" for ns in (open_namespaces or [])]
    # Decide if statement is a `def := <expr>` form (no tactic) or `theorem ... := by` form
    if statement.strip().endswith(":= by"):
        body = f"{statement}\n  {tactic_block}"
    elif " := by" in statement:
        body = f"{statement}\n  {tactic_block}"
    elif statement.startswith("noncomputable def") or statement.startswith("def"):
        # term-mode def; tactic doesn't apply directly. Wrap as theorem.
        body = statement  # use as-is; hammers don't apply
    else:
        body = f"{statement} := by\n  {tactic_block}"
    return "\n".join(imports + opens + ["", body, ""])


def lake_compile(lean_src: str, slug: str, keep_files: bool = False) -> dict:
    sys.path.insert(0, str(REPO / "src"))
    from src.ztare.gates.lean_proof_gate import write_lean_target
    from lean_fast_compile import compile_lean_fast_combined_output
    proofs_root = REPO / "ztare_proofs"
    target = write_lean_target(lean_src, slug, proofs_root)
    result = compile_lean_fast_combined_output(
        target, proofs_root, timeout_seconds=90)
    result["lean_path"] = str(target)
    if not keep_files:
        try:
            target.unlink()
        except OSError:
            pass
    return result


def try_hammer(statement: str, tactic_name: str, tactic_block: str,
                slug_base: str, imports: list[str] | None = None,
                open_namespaces: list[str] | None = None,
                keep_files: bool = False) -> dict:
    slug = f"{slug_base}_{tactic_name}"
    lean_src = build_lean_file(
        statement, tactic_block, imports=imports,
        open_namespaces=open_namespaces)
    try:
        result = lake_compile(lean_src, slug, keep_files=keep_files)
    except Exception as e:
        return {"tactic": tactic_name, "compiled": False,
                "error": f"{type(e).__name__}: {e}",
                "stdout_tail": "", "stderr_tail": ""}
    return {
        "tactic": tactic_name,
        "compiled": result.get("compiled", False),
        "exit_code": result.get("exit_code"),
        "duration_s": result.get("duration_s"),
        "stdout_tail": (result.get("stdout") or "")[-600:],
        "stderr_tail": (result.get("stderr") or "")[-600:],
        "lean_path": result.get("lean_path", ""),
    }


def run_hammer(target: str, field: str, patch_class: str,
                field_type: str | None, statement_override: str | None = None,
                imports: list[str] | None = None,
                open_namespaces: list[str] | None = None,
                keep_files: bool = False) -> dict:
    statement_is_synthetic = statement_override is None
    statement = statement_override or synthesize_statement(
        target, field, patch_class, field_type)
    print(f"[hammer] target={target} field={field} class={patch_class}")
    print(f"  statement: {statement[:120]}")
    if statement_is_synthetic:
        print("  mode: synthetic smoke statement (success is not a proof-spine closure)")
    else:
        print("  mode: caller-supplied theorem statement")
    target_safe = re.sub(r"[^A-Za-z0-9_]", "_", target).lower()[:25]
    slug_base = f"hammer_{target_safe}_{field[:15]}_{patch_class[:15]}"

    results = []
    for tactic_name, tactic_block in HAMMER_TACTICS:
        # Skip tactic block for term-mode defs (anonymous constructor)
        if statement.startswith("noncomputable def"):
            # Tactics don't apply to term-mode body; only the bare def is the test
            r = try_hammer(
                statement, "term_mode_only", "", slug_base, imports,
                open_namespaces, keep_files)
            r["tactic"] = "term_mode_only"
            results.append(r)
            break  # one shot for term-mode
        if tactic_name == "polyrith":
            continue
        r = try_hammer(
            statement, tactic_name, tactic_block, slug_base, imports,
            open_namespaces, keep_files)
        results.append(r)
        if r["compiled"]:
            print(f"  ✓ {tactic_name} discharged the goal "
                  f"(duration={r.get('duration_s', '?')}s)")
            break
        else:
            print(f"  ✗ {tactic_name}")

    success = next((r for r in results if r["compiled"]), None)
    return {
        "target": target, "field": field, "patch_class": patch_class,
        "statement": statement,
        "statement_is_synthetic": statement_is_synthetic,
        "results": results,
        "succeeded_with": success["tactic"] if success else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--field", required=True)
    ap.add_argument("--patch-class", default="instance_with_evidence",
                    choices=["transitivity_adapter", "branch_wise_falsifier",
                             "source_provenance_bridge", "instance_with_evidence"])
    ap.add_argument("--field-type", default=None,
                    help="explicit field type (e.g. 'NSContinuationCriterion')")
    ap.add_argument("--statement", default=None,
                    help=("caller-supplied Lean theorem header ending in ':= by'; "
                          "required for proof-spine credit"))
    ap.add_argument("--import-module", action="append", default=[],
                    help=("extra Lean import module; may be repeated. "
                          "Defaults remain Mathlib.Tactic + ns_phase_latency_clay_bridge"))
    ap.add_argument("--open-namespace", action="append", default=[],
                    help="Lean namespace to open after imports; may be repeated")
    ap.add_argument("--keep-files", action="store_true",
                    help="keep generated hammer Lean files for inspection")
    ap.add_argument("--out", type=Path,
                    default=REPO / "analytics" / "public" / "queries" /
                              "lean_hammer_results.jsonl")
    args = ap.parse_args()

    # Auto-resolve field type if not given
    if not args.field_type:
        sys.path.insert(0, str(REPO))
        try:
            from typed_endpoint_pack import (
                load_workmap_target, resolve_field
            )
            target_obj = load_workmap_target(args.target)
            if target_obj:
                f = resolve_field(target_obj, args.field)
                if f:
                    args.field_type = f.get("type_head")
                    print(f"  auto-resolved field type: {args.field_type}")
        except Exception as e:
            print(f"  field type resolution failed: {e}")

    imports = None
    if args.import_module:
        imports = ["import Mathlib.Tactic"] + [
            f"import {module}" for module in args.import_module
        ]
    result = run_hammer(args.target, args.field, args.patch_class,
                         args.field_type, args.statement, imports,
                         args.open_namespace, args.keep_files)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("a") as f:
        f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(),
                              **result}) + "\n")

    print(f"\n=== HAMMER RESULT ===")
    if result["succeeded_with"]:
        if result["statement_is_synthetic"]:
            print(f"  ✓ SMOKE PASSED via tactic: {result['succeeded_with']}")
            print("  Synthetic statement only; do not count as theorem progress.")
            return 2
        else:
            print(f"  ✓ VERIFIED via tactic: {result['succeeded_with']}")
            print("  Caller-supplied statement compiled with zero LLM tokens.")
            return 0
    else:
        n_tried = len(result["results"])
        print(f"  ✗ all {n_tried} hammers failed")
        print(f"  → fall through to LLM with hint: tried {[r['tactic'] for r in result['results']]}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
