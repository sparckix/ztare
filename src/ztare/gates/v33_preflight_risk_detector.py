#!/usr/bin/env python3
"""v33_preflight_risk_detector.py — the governance harness's missing organ.

Closes the gap the operator flagged: tick541 / carleman vacuity was caught
OFFLINE by GPT-5.5, NOT by the harness. This builds the preflight,
statement-level, LEAKAGE-INDEPENDENT vacuity/risk detector + an independent
Lean verifier that confirms vacuity WITHOUT any audit verdict.

This is the leakage-independent failure-attestation mechanism the converged
terminal finding said was missing. It is primitive-first and immediately
validatable on documented ground truth.

Two components:
  1. detect_risks(statement)  — deterministic statement-shape flags, NO proof,
     NO audit verdict. Flags:
       - vacuous_True_hypothesis     : a hypothesis of type exactly `True`
       - vacuous_trivial_exists_hyp  : `∃ x : T, <trivially-satisfiable>`
       - vacuous_exists_prop_concl   : conclusion `∃ _ : Prop, _`  (⟨True,trivial⟩)
       - literal_True_conclusion     : conclusion is `True`
       - opaque_predicate_present    : statement uses `opaque` (REAL content — anti-flag)
  2. independent_verify(stmt, imports, sandbox) — synthesize a probe
     `example : <stmt> := by (first | trivial | exact ⟨trivial⟩ | tauto | simp)`
     and Lean-compile. If it closes by a trivial tactic → vacuity CONFIRMED,
     leakage-independent (no reference to any kill verdict).

Ground-truth validation built in (--validate): the pre-fix carleman
backward-uniqueness pattern (MUST flag) vs the opaque-fixed version
(MUST NOT flag).
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
DEFAULT_SANDBOX = ROOT / ("analytics/public/leanmill/external_benchmarks/"
                          "sandboxes/v28A_carleson_baseline/carleson")
LEAN_ERR_RE = re.compile(r"^\S*\.lean:\d+:\d+: error:", re.MULTILINE)


# ---------------------------------------------------------------------------
# Component 1 — deterministic statement-shape risk detector (NO proof, NO audit)
# ---------------------------------------------------------------------------

def detect_risks(statement: str) -> dict:
    """statement = the Lean type (hypotheses + conclusion), no `:= proof`."""
    s = statement
    flags: list[str] = []

    # opaque present → real content, strong ANTI-vacuity signal
    has_opaque = bool(re.search(r"\bopaque\b", s))

    # Split hypotheses (paren / bracket binders) from conclusion (after last top-level `:`)
    # Hypotheses of literal type True:  `(name : True)` or `: True →` or `, True →`
    if re.search(r"\(\s*[\w']+\s*:\s*True\s*\)", s) or re.search(r":\s*True\s*(?:→|\bto\b)", s):
        flags.append("vacuous_True_hypothesis")

    # Trivially-satisfiable existential hypothesis: ∃ x : ℝ, 0 < x  /  ∃ _ : ℕ, _  etc.
    for m in re.finditer(r"∃\s*[\w']+\s*:\s*(ℝ|ℕ|ℤ|Nat|Real|Int)\s*,\s*([^,()]+?)(?:\)|,|→|$)", s):
        body = m.group(2).strip()
        if re.match(r"0\s*<\s*[\w']+$", body) or re.match(r"[\w']+\s*>\s*0$", body) \
           or body in ("True",) or re.match(r"[\w']+\s*=\s*[\w']+$", body):
            flags.append("vacuous_trivial_exists_hyp")
            break

    # ∃ _ : Prop, _   conclusion (the ⟨True, trivial⟩ shape)
    if re.search(r"∃\s*[\w']+\s*:\s*Prop\s*,\s*[\w']+\s*$", s) or \
       re.search(r"∃\s*[\w']+\s*:\s*Prop\s*,\s*[\w']+\s*\)?\s*$", s):
        flags.append("vacuous_exists_prop_concl")

    # conclusion literally True (last top-level token)
    if re.search(r"(?::|→|,)\s*True\s*$", s.strip()):
        flags.append("literal_True_conclusion")

    # single-lemma-exact candidate: very short statement, single relation, no binders chain
    if len(s) < 90 and s.count("→") == 0 and s.count("∀") <= 1 and ("=" in s or "≤" in s or "<" in s):
        flags.append("single_lemma_exact_candidate")

    return {
        "statement_preview": s.strip()[:200],
        "risk_flags": sorted(set(flags)),
        "opaque_predicate_present": has_opaque,
        "vacuity_suspected": (not has_opaque) and any(
            f.startswith("vacuous_") or f == "literal_True_conclusion" for f in flags
        ),
    }


# ---------------------------------------------------------------------------
# Component 2 — independent Lean verifier (confirms vacuity, NO audit verdict)
# ---------------------------------------------------------------------------

def independent_verify(statement: str, imports: list[str], sandbox: Path,
                       timeout: int = 60) -> dict:
    """Synthesize `example : <statement> := by <trivial-cascade>` and compile.
    If it closes by a trivial tactic, vacuity is CONFIRMED leakage-independent.
    """
    if not sandbox.exists():
        return {"verified": None, "error": f"sandbox missing: {sandbox}"}
    imp = "\n".join(imports) if imports else "import Mathlib"
    probe = (
        f"{imp}\n\n"
        f"-- v33 independent vacuity probe (no audit verdict referenced)\n"
        f"example : {statement.strip()} := by\n"
        f"  first\n"
        f"  | trivial\n"
        f"  | exact ⟨trivial⟩\n"
        f"  | exact ⟨True, trivial⟩\n"
        f"  | exact ⟨1, by norm_num⟩\n"
        f"  | tauto\n"
        f"  | simp_all\n"
    )
    tmpdir = sandbox / "V33VacuityProbe"
    tmpdir.mkdir(exist_ok=True)
    tf = tempfile.NamedTemporaryFile(mode="w", suffix=".lean", dir=str(tmpdir), delete=False)
    tf.write(probe)
    tf.close()
    rel = Path(tf.name).relative_to(sandbox)
    started = time.time()
    try:
        proc = subprocess.run(
            ["nice", "-n", "10", "lake", "env", "lean", str(rel)],
            cwd=str(sandbox), text=True, capture_output=True, timeout=timeout, check=False,
        )
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        err = bool(LEAN_ERR_RE.search(out))
        closed_trivially = (proc.returncode == 0) and (not err)
        return {
            "verified": closed_trivially,         # True = vacuity CONFIRMED independently
            "elapsed_s": round(time.time() - started, 2),
            "probe_preview": probe[:400],
            "error_tail": out[-300:] if err else "",
        }
    except subprocess.TimeoutExpired:
        return {"verified": None, "timed_out": True, "elapsed_s": timeout}
    except Exception as e:
        return {"verified": None, "error": str(e)}


# ---------------------------------------------------------------------------
# Ground-truth validation
# ---------------------------------------------------------------------------

GT_POSITIVE = {  # documented-vacuous (pre-fix carleman). detector MUST flag.
    "name": "carleman_prefix_vacuous",
    "statement": "(parabolic_equation : True) → (vanishing_at_tip : ∃ ρ : ℝ, 0 < ρ) → ∃ vanishing_certificate : Prop, vanishing_certificate",
}
GT_NEGATIVE = {  # opaque-fixed version. detector MUST NOT flag (real content).
    "name": "carleman_opaque_fixed",
    "statement": "(hcone : ParabolicEquationOnBackwardCone data v T x r) → (htip : VanishingOnSpatialNeighborhood v T x) → BackwardUniquenessConcluded v T x r",
}


def run_validation() -> dict:
    pos = detect_risks(GT_POSITIVE["statement"])
    neg = detect_risks(GT_NEGATIVE["statement"])
    pos_ok = pos["vacuity_suspected"] is True
    neg_ok = neg["vacuity_suspected"] is False
    verdict = "DETECTOR_VALIDATED" if (pos_ok and neg_ok) else "DETECTOR_FAILS_GROUND_TRUTH"
    return {
        "ground_truth_positive": {**GT_POSITIVE, "detected": pos, "expected_vacuous": True, "pass": pos_ok},
        "ground_truth_negative": {**GT_NEGATIVE, "detected": neg, "expected_vacuous": False, "pass": neg_ok},
        "verdict": verdict,
        "rationale": (
            "detector flags the documented pre-fix carleman vacuity (True-hyp + "
            "trivial-∃-hyp + ∃Prop-concl) AND does NOT flag the opaque-fixed "
            "version — leakage-independent, preflight, no audit verdict used."
            if verdict == "DETECTOR_VALIDATED" else
            f"pos_ok={pos_ok} neg_ok={neg_ok} — shape rules need refinement"
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true", help="run ground-truth validation")
    ap.add_argument("--statement", default=None, help="classify a single Lean statement")
    ap.add_argument("--verify", action="store_true", help="also run independent Lean verifier")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.validate:
        res = run_validation()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        if args.out:
            Path(args.out).write_text(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["verdict"] == "DETECTOR_VALIDATED" else 1

    if args.statement:
        r = detect_risks(args.statement)
        if args.verify:
            r["independent_verify"] = independent_verify(args.statement, ["import Mathlib"], DEFAULT_SANDBOX)
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
