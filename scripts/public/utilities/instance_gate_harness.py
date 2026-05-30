#!/usr/bin/env python3
"""Substrate-agnostic gate-pipeline harness for instance-construction candidates.

Orchestrates the already-shipped ZTARE gate stack on a candidate
proposal (a parametric form, optional Lean source, optional simulator
hook). Every gate this harness wires is substrate-agnostic by design;
the harness itself takes no NS / FIGS / millennium opinion. Substrate
specifics live in the candidate JSON.

# Pipeline

A "candidate" is a JSON dict. Gates run in order; each is pass / fail /
indeterminate / skipped. First hard_fail short-circuits unless
`--continue-on-fail` is set.

  1. symbolic_logic_cage (GP-170)
       Algebraic constraints on the parametric form (SymPy / Z3).
       Skipped if no `algebraic_constraints` block.
  2. buckingham_pi_gate
       Dimensional homogeneity check. Skipped if no
       `feature_dimensions` block.
  3. translation_diff_gate (G5, GP-211 family)
       Hash-canonicalisation between source expression and target
       statement (typical use: sympy ↔ Lean). Skipped unless both
       `pre_translation_expression` and `post_translation_lean_statement`
       are present.
  4. lean_proof_gate (GP-211)
       `lake build` on synthesised Lean target. Skipped in `--stub`
       mode or if `lean_source` is absent.
  5. simulation_gate (pluggable)
       Optional numerical falsifier. Substrate provides a dotted
       Python entry-point in `simulation.entry_point` (e.g.
       "package.module:function") plus kwargs in `simulation.kwargs`.
       The callable returns a dict with at least `passed: bool` and
       optional `metrics`. Skipped in `--stub` mode or when no
       entry_point is declared.

# Stub mode

`--stub` skips lake/lean and the simulation entry-point, runs only the
pure-Python gates (symbolic_logic_cage, buckingham_pi, translation_diff
hash branch). Lets us validate wiring on a contrived candidate before
plumbing into the real autoresearch loop.

# Status

ADVISORY v0.1. The gates are existing ZTARE infrastructure; the
orchestrator is the new code.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


@dataclass
class GateOutcome:
    name: str
    verdict: str  # "passed" | "failed" | "indeterminate" | "skipped"
    reason: str = ""
    detail: dict[str, Any] = field(default_factory=dict)
    hard_fail: bool = False


def _fmt(o: GateOutcome) -> str:
    sym = {"passed": "OK ", "failed": "X  ",
           "indeterminate": "?  ", "skipped": "-  "}.get(o.verdict, "?  ")
    return f"[{sym}] {o.name:<25} {o.verdict:<14} {o.reason}"


# ---------------------------------------------------------------------------
# Gate 1 — symbolic_logic_cage (GP-170)
# ---------------------------------------------------------------------------

def gate_symbolic_logic_cage(candidate: dict) -> GateOutcome:
    constraints = candidate.get("algebraic_constraints") or []
    parametric_form = candidate.get("parametric_form")
    if not constraints:
        return GateOutcome("symbolic_logic_cage", "skipped",
                           "no algebraic_constraints declared")
    if not parametric_form:
        return GateOutcome("symbolic_logic_cage", "skipped",
                           "no parametric_form declared")
    from src.ztare.gates.symbolic_logic_cage import check_algebraic_constraints
    try:
        result = check_algebraic_constraints(
            form_str=parametric_form,
            constraints=constraints,
            init_ranges=candidate.get("init_ranges", {}),
            feature_dimensions=candidate.get("feature_dimensions", {}),
        )
    except Exception as e:
        return GateOutcome("symbolic_logic_cage", "indeterminate",
                           f"sympy raised: {type(e).__name__}: {e}")
    verdict_map = {
        "passed": "passed",
        "violated": "failed",
        "rejected_form": "failed",
        "data_disagreement": "failed",
        "indeterminate": "indeterminate",
        "budget_exceeded": "indeterminate",
    }
    overall = result.overall
    return GateOutcome(
        name="symbolic_logic_cage",
        verdict=verdict_map.get(overall, "indeterminate"),
        reason=overall + (f": {result.rejected_reason}" if result.rejected_reason else ""),
        detail={"per_constraint": [str(v) for v in (result.per_constraint or [])][:5],
                "diagnostics": result.diagnostics[:5]},
        hard_fail=overall in ("violated", "rejected_form", "data_disagreement"),
    )


# ---------------------------------------------------------------------------
# Gate 2 — buckingham_pi_gate
# ---------------------------------------------------------------------------

def gate_buckingham_pi(candidate: dict) -> GateOutcome:
    feat_dims = candidate.get("feature_dimensions") or {}
    parametric_form = candidate.get("parametric_form")
    if not parametric_form:
        return GateOutcome("buckingham_pi", "skipped", "no parametric_form")
    if not feat_dims:
        return GateOutcome("buckingham_pi", "skipped", "no feature_dimensions")
    from src.ztare.gates.buckingham_pi_gate import run_buckingham_pi_gate
    try:
        result = run_buckingham_pi_gate(
            parametric_form=parametric_form,
            rubric_data={"dimensional_features": feat_dims},
        )
    except Exception as e:
        return GateOutcome("buckingham_pi", "indeterminate",
                           f"raised: {type(e).__name__}: {e}")
    passed = bool(result.get("passed", False))
    return GateOutcome(
        name="buckingham_pi",
        verdict="passed" if passed else "failed",
        reason=(f"{len(result.get('violations', []))} violation(s)"
                if not passed else "dimensionally homogeneous"),
        detail={"violations": result.get("violations", [])[:5]},
        hard_fail=not passed,
    )


# ---------------------------------------------------------------------------
# Gate 3 — translation_diff_gate (G5)
# ---------------------------------------------------------------------------

def gate_translation_diff(candidate: dict) -> GateOutcome:
    pre = candidate.get("pre_translation_expression")
    post = candidate.get("post_translation_lean_statement")
    if not (pre and post):
        return GateOutcome(
            "translation_diff", "skipped",
            "needs pre_translation_expression + post_translation_lean_statement",
        )
    from src.ztare.gates.translation_diff_gate import run_gate as run_g5
    try:
        result = run_g5(
            claim={"pre_translation_expression": pre,
                   "post_translation_lean_statement": post},
            rubric_params={},
        )
    except Exception as e:
        return GateOutcome("translation_diff", "indeterminate",
                           f"raised: {type(e).__name__}: {e}")
    passed = result.get("passed")
    verdict = ("passed" if passed is True
               else "failed" if passed is False
               else "indeterminate")
    return GateOutcome(
        name="translation_diff",
        verdict=verdict,
        reason=result.get("reason", ""),
        detail={"actual": result.get("actual"),
                "threshold": result.get("threshold")},
        hard_fail=bool(result.get("hard_fail")),
    )


# ---------------------------------------------------------------------------
# Gate 4 — lean_proof_gate (lake build + axiom/forbidden-token audit)
# ---------------------------------------------------------------------------

def gate_lean_proof(candidate: dict, *, stub: bool, project_slug: str,
                    proofs_root: Path) -> GateOutcome:
    if stub:
        return GateOutcome("lean_proof", "skipped", "stub mode")
    lean_source = candidate.get("lean_source")
    if not lean_source:
        return GateOutcome("lean_proof", "skipped", "no lean_source declared")
    from src.ztare.gates.lean_proof_gate import (
        audit_axioms,
        compile_lean,
        write_lean_target,
    )
    try:
        target = write_lean_target(lean_source, project_slug, proofs_root)
        compile_result = compile_lean(target, proofs_root)
        audit_result = (
            audit_axioms(target, proofs_root)
            if compile_result.get("compiled")
            else {
                "axiom_audit_passed": False,
                "extra_axioms": [],
                "forbidden_tokens": [],
            }
        )
    except Exception as e:
        return GateOutcome("lean_proof", "indeterminate",
                           f"raised: {type(e).__name__}: {e}")
    compiled = bool(compile_result.get("compiled"))
    audit_passed = bool(audit_result.get("axiom_audit_passed"))
    passed = compiled and audit_passed and not audit_result.get("forbidden_tokens")
    if not compiled:
        reason = f"lake build failed (exit={compile_result.get('exit_code')})"
    elif not audit_passed:
        reason = "lean audit failed (no theorem/lemma, forbidden tokens, or extra axioms)"
    else:
        reason = "lake build and lean audit succeeded"
    return GateOutcome(
        name="lean_proof",
        verdict="passed" if passed else "failed",
        reason=reason,
        detail={"duration_s": compile_result.get("duration_s"),
                "stderr_tail": (compile_result.get("stderr") or "")[-500:],
                "extra_axioms": audit_result.get("extra_axioms"),
                "forbidden_tokens": audit_result.get("forbidden_tokens")},
        hard_fail=not passed,
    )


# ---------------------------------------------------------------------------
# Gate 5 — simulation_gate (pluggable substrate-specific simulator)
# ---------------------------------------------------------------------------

def gate_simulation(candidate: dict, *, stub: bool) -> GateOutcome:
    spec = candidate.get("simulation") or {}
    entry_point = spec.get("entry_point")
    if not entry_point:
        return GateOutcome("simulation", "skipped",
                           "no simulation.entry_point declared")
    if stub:
        return GateOutcome("simulation", "skipped",
                           f"stub mode: would call {entry_point}")
    if ":" not in entry_point:
        return GateOutcome("simulation", "indeterminate",
                           f"entry_point must be 'module:function', got {entry_point!r}")
    mod_name, fn_name = entry_point.split(":", 1)
    try:
        mod = importlib.import_module(mod_name)
        fn = getattr(mod, fn_name)
    except Exception as e:
        return GateOutcome("simulation", "indeterminate",
                           f"import failed: {type(e).__name__}: {e}")
    kwargs = spec.get("kwargs", {}) or {}
    try:
        result = fn(**kwargs)
    except Exception as e:
        return GateOutcome("simulation", "indeterminate",
                           f"simulator raised: {type(e).__name__}: {e}")
    if not isinstance(result, dict):
        return GateOutcome("simulation", "indeterminate",
                           f"simulator must return dict, got {type(result).__name__}")
    passed = result.get("passed")
    verdict = ("passed" if passed is True
               else "failed" if passed is False
               else "indeterminate")
    return GateOutcome(
        name="simulation",
        verdict=verdict,
        reason=str(result.get("reason", "")),
        detail={"metrics": result.get("metrics", {})},
        hard_fail=(passed is False),
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_pipeline(candidate: dict, *, stub: bool, project_slug: str,
                 proofs_root: Path, continue_on_fail: bool) -> list[GateOutcome]:
    gates = [
        lambda c: gate_symbolic_logic_cage(c),
        lambda c: gate_buckingham_pi(c),
        lambda c: gate_translation_diff(c),
        lambda c: gate_lean_proof(c, stub=stub, project_slug=project_slug,
                                  proofs_root=proofs_root),
        lambda c: gate_simulation(c, stub=stub),
    ]
    outcomes: list[GateOutcome] = []
    for fn in gates:
        outcome = fn(candidate)
        outcomes.append(outcome)
        if outcome.hard_fail and not continue_on_fail:
            break
    return outcomes


def summarise(outcomes: list[GateOutcome]) -> dict:
    counts: dict[str, int] = {}
    for o in outcomes:
        counts[o.verdict] = counts.get(o.verdict, 0) + 1
    overall = (
        "REJECT" if any(o.hard_fail for o in outcomes)
        else "ACCEPT" if all(o.verdict in ("passed", "skipped") for o in outcomes)
        else "INDETERMINATE"
    )
    return {"verdict_counts": counts, "overall": overall}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--candidate", type=Path, required=True,
                    help="Path to candidate JSON")
    ap.add_argument("--stub", action="store_true",
                    help="Skip lake/lean and external simulator")
    ap.add_argument("--continue-on-fail", action="store_true",
                    help="Run every gate even after a hard_fail")
    ap.add_argument("--project-slug", default="instance_iter",
                    help="Lean module slug if lean_proof gate runs")
    ap.add_argument("--proofs-root", type=Path, default=REPO / "ztare_proofs")
    ap.add_argument("--out", type=Path,
                    help="Optional path to dump full result JSON")
    args = ap.parse_args()

    candidate = json.loads(args.candidate.read_text())
    print(f"=== gate-pipeline harness: {candidate.get('name', '<unnamed>')} ===")
    if candidate.get("target"):
        print(f"target: {candidate['target']}")
    print(f"stub: {args.stub}")
    print()

    outcomes = run_pipeline(
        candidate,
        stub=args.stub,
        project_slug=args.project_slug,
        proofs_root=args.proofs_root,
        continue_on_fail=args.continue_on_fail,
    )
    for o in outcomes:
        print(_fmt(o))

    summary = summarise(outcomes)
    print()
    print(f"verdict counts: {summary['verdict_counts']}")
    print(f"OVERALL: {summary['overall']}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({
            "candidate_name": candidate.get("name"),
            "target": candidate.get("target"),
            "stub": args.stub,
            "outcomes": [asdict(o) for o in outcomes],
            "summary": summary,
        }, indent=2, default=str))
        print(f"wrote {args.out}")

    return 0 if summary["overall"] != "REJECT" else 1


if __name__ == "__main__":
    sys.exit(main())
