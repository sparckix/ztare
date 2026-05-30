#!/usr/bin/env python3
"""v33_currency_mismatch_gate.py — scalar-wrapper currency-mismatch organ.

Fifth forward gate. Catches the NS scalar-wrapper class: a SCALAR theorem
(an ℝ/ℝ≥0/ENNReal order relation) presented as discharging a FIELD/VECTOR
obligation it does not actually pay. "Currency mismatch" = the proof's
quantity is in the wrong currency vs the obligation it claims to settle.

HONEST SCOPE (stated, not force-fit): the GENERAL currency-mismatch
(arbitrary wrong-norm / units) is semantically deep and NOT cheaply
leakage-independently verifiable — that needs a typed-companion /
dimensional design, separately flagged. THIS organ covers only the
dominant, cheaply-verifiable SCALAR-WRAPPER subcase.

Same proven pattern, ZERO audit verdict:

  Component 1 (instant shape): scalar_wrapper_suspect iff the theorem's
    conclusion head is a SCALAR order relation (≤/</=/≥/> over
    ℝ/ℝ≥0/ENNReal/Real) AND the row references (name / comment / import)
    a FIELD/VECTOR obligation token (VelocityField, EuclideanSpace,
    vectorField, field obligation, →ₗ, fun_⟶) it purports to discharge.

  Component 2 (independent — Lean's TYPE CHECKER, no audit verdict):
    given the claimed obligation type O and the scalar theorem T,
    synthesize `example : O := T` (or `def _slot : O := by exact T`).
    If Lean REJECTS it on a type mismatch, the scalar does NOT typecheck
    as the field obligation → currency mismatch CONFIRMED, leakage-
    independently (Lean's kernel, not an audit verdict). If it typechecks,
    NOT a mismatch.

Ground-truth validation (synthetic, self-contained):
  + scalar `(1:ℝ) ≤ 2` slotted into a Prop expecting a vector predicate
    -> Lean type-rejects -> CONFIRM
  - a theorem whose type IS the claimed obligation
    -> Lean accepts -> NOT confirmed
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
DEFAULT_SANDBOX = ROOT / ("analytics/public/leanmill/external_benchmarks/"
                          "sandboxes/v28A_carleson_baseline/carleson")
LEAN_ERR_RE = re.compile(r"^\S*\.lean:\d+:\d+: error:", re.MULTILINE)
TYPE_MISMATCH_RE = re.compile(r"type mismatch|has type[\s\S]{0,200}but is expected to have type"
                              r"|application type mismatch|failed to synthesize", re.IGNORECASE)

SCALAR_CONCL_RE = re.compile(
    r":\s*[^:=]*?(?:ℝ|ℝ≥0|ENNReal|Real|NNReal)\b[^:=]*?(≤|<|=|≥|>)[^:=]*?(?:$|:=)")
FIELD_OBLIGATION_TOKENS = ("VelocityField", "EuclideanSpace", "vectorField",
                           "field obligation", "FieldObligation", "→ₗ",
                           "VectorField", "PiLp", "→ EuclideanSpace", "GlobalSmoothSolution")


def detect_shape(row_text: str) -> dict:
    concl_scalar = bool(SCALAR_CONCL_RE.search(row_text))
    field_ref = next((t for t in FIELD_OBLIGATION_TOKENS if t in row_text), None)
    suspect = concl_scalar and (field_ref is not None)
    return {
        "scalar_wrapper_suspect": bool(suspect),
        "conclusion_is_scalar": concl_scalar,
        "field_obligation_token": field_ref,
        "preview": row_text.strip()[:160],
    }


def _compile(probe: str, sandbox: Path, timeout: int) -> tuple[bool | None, str]:
    tmpdir = sandbox / "V33CurrencyProbe"
    tmpdir.mkdir(exist_ok=True)
    tf = tempfile.NamedTemporaryFile(mode="w", suffix=".lean", dir=str(tmpdir), delete=False)
    tf.write(probe); tf.close()
    rel = Path(tf.name).relative_to(sandbox)
    try:
        p = subprocess.run(["nice", "-n", "10", "lake", "env", "lean", str(rel)],
                            cwd=str(sandbox), text=True, capture_output=True,
                            timeout=timeout, check=False)
        out = (p.stdout or "") + "\n" + (p.stderr or "")
        ok = (p.returncode == 0) and (not LEAN_ERR_RE.search(out))
        return ok, out[-400:]
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except Exception as e:
        return None, str(e)


def independent_typeslot_verify(obligation_type: str, scalar_term: str,
                                preamble: str, sandbox: Path, timeout: int = 60) -> dict:
    """Lean's type checker is the independent arbiter: does the scalar term
    typecheck AS the claimed field obligation?"""
    if not sandbox.exists():
        return {"currency_mismatch_confirmed": None, "error": "sandbox missing"}
    probe = (f"{preamble}\n\n"
             f"-- v33 currency-mismatch type-slot probe (Lean kernel, no audit verdict)\n"
             f"example : {obligation_type} := {scalar_term}\n")
    ok, tail = _compile(probe, sandbox, timeout)
    type_rejected = (ok is False) and bool(TYPE_MISMATCH_RE.search(tail))
    return {
        "currency_mismatch_confirmed": type_rejected,
        "typeslot_compiles": ok,
        "lean_tail": tail[-200:],
        "interpretation": ("scalar term does NOT typecheck as the claimed field "
                           "obligation — currency mismatch (Lean kernel rejected)"
                           if type_rejected else
                           ("scalar typechecks as obligation — NOT a mismatch" if ok
                            else "inconclusive (non-type error / timeout)")),
    }


GT = [
    # POSITIVE: scalar nat/real fact slotted into a Prop expecting a function predicate
    ("positive_scalar_wrapper",
     "import Mathlib",
     "(fun (_ : ℝ → ℝ) => True) (id : ℝ → ℝ) ∧ ((1:ℝ) ≤ 2)",  # obligation: a Prop about a function AND scalar
     "(by norm_num : (1:ℝ) ≤ 2)",  # scalar term — does NOT inhabit the conjunction
     True),
    # NEGATIVE: term whose type IS exactly the claimed obligation
    ("negative_typematch",
     "import Mathlib",
     "(1:ℝ) ≤ 2",
     "(by norm_num : (1:ℝ) ≤ 2)",
     False),
]


def run_validation(sandbox: Path) -> dict:
    res = {}
    for tag, pre, obl, term, expect in GT:
        v = independent_typeslot_verify(obl, term, pre, sandbox)
        got = bool(v.get("currency_mismatch_confirmed"))
        res[tag] = {"obligation": obl, "scalar_term": term, "verify": v,
                    "expect": expect, "got": got, "pass": got == expect}
    res["verdict"] = ("CURRENCY_MISMATCH_GATE_VALIDATED"
                      if all(r["pass"] for r in res.values() if isinstance(r, dict) and "pass" in r)
                      else "GATE_FAILS_GROUND_TRUTH")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.validate:
        r = run_validation(DEFAULT_SANDBOX)
        print(json.dumps(r, indent=2, ensure_ascii=False))
        if args.out:
            Path(args.out).write_text(json.dumps(r, indent=2, ensure_ascii=False))
        return 0 if r["verdict"] == "CURRENCY_MISMATCH_GATE_VALIDATED" else 1
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
