"""CONTROLLED closure-lift for the exogenous transport edges (#139) — Gröbner→linear_combination and
SOS→nlinarith-hints — measured HONESTLY, both arms kernel-verified on the SAME goals, warm-local.

  • BASELINE = a fair LOCAL native attempt (nlinarith/linarith/ring/positivity, hyps in context). NOTE:
    `polyrith` (the real Gröbner competitor, itself Gröbner-based) needs a network Sage call and is NOT
    exercised here — so a lift measured below is a lift over the LOCAL deterministic cascade, and the
    polyrith comparison is explicitly UNMEASURED (flagged, not hidden).
  • TREATMENT (Gröbner) = groebner_certificate(hyps, goal) → `linear_combination <cofactors>` → kernel-verify.
  • TREATMENT (SOS)     = sos_certificate(poly) → `nlinarith [<sos hints>]` → kernel-verify.

LIFT = treatment_closed − baseline_closed on the discriminating rows. Corpus mixes EASY controls (native
should close ⇒ subsumed) with degree-≥3 / multivariate rows (native should fail ⇒ the lift candidates).

  PYTHONPATH=src ./venv/bin/python projects/leanmill_experiments/transport_lift_controlled.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
SANDBOX = str(REPO / "ztare_proofs")
TIMEOUT = 60

from ztare.common.groebner_cert import groebner_certificate
from ztare.common.sos_certificate import sos_certificate
from ztare.formal.repl_compile import compile_probe_via_repl


def _kv(full_src: str) -> bool:
    """Kernel-verify a whole-file proof warm: compiles, no error, no sorry."""
    try:
        r = compile_probe_via_repl(full_src, SANDBOX, timeout=TIMEOUT, reject_sorry=True)
        return bool(r and r[0])
    except Exception:  # noqa: BLE001
        return False


# (label, vardecl, hyps[list of "lhs = rhs"], conclusion, is_control)  — Gröbner ideal-membership equalities
GROEBNER = [
    ("groeb_easy_sq",   "a b : ℝ",   ["a = b"],                 "a^2 = b^2",                 True),
    ("groeb_easy_chain","x y z : ℝ", ["x = y + 1", "y = z^2"],  "x = z^2 + 1",               True),
    ("groeb_cubic_sum", "a b c : ℝ", ["a + b + c = 0"],         "a^3 + b^3 + c^3 = 3*a*b*c", False),  # degree 3
    ("groeb_sym2",      "a b : ℝ",   ["a + b = 3", "a*b = 2"],  "a^2 + b^2 = 5",             False),  # nonlinear hyps
]
# (label, var, poly ≥ 0, is_control)  — SOS nonnegativity
SOS = [
    ("sos_easy_sq",   "x", "x^2 + 1",            True),
    ("sos_quartic",   "x", "x^4 - 2*x^2 + 1",    False),  # (x^2-1)^2, degree 4
    ("sos_deg6",      "x", "x^6 - 3*x^4 + 3*x^2",False),  # x^2(x^2-1)^2 ... degree 6
]
# Fair LOCAL native baseline. `polyrith` (the historical Gröbner competitor) is DECOMMISSIONED in current
# Mathlib ("no longer available, the external service it relied on" is dead) — so it is NOT a competitor.
# `subst_vars` is included so a `var=expr` hyp is substituted (removes the a=b⊢a²=b² baseline artifact).
_NATIVE = ["subst_vars; ring", "subst_vars; nlinarith [{h}]", "nlinarith [{h}]", "linarith [{h}]",
           "nlinarith", "ring", "positivity"]


def _native_closes(vardecl, hyps, concl, name) -> bool:
    hyp_decl = "".join(f" (h{i} : {h})" for i, h in enumerate(hyps))
    hlist = ", ".join(f"h{i}" for i in range(len(hyps)))
    for tac in _NATIVE:
        t = tac.format(h=hlist) if "{h}" in tac else tac
        src = f"import Mathlib\n\ntheorem {name} ({vardecl}){hyp_decl} : {concl} := by\n  {t}\n"
        if _kv(src):
            return True
    return False


def main() -> int:
    print("=== TRANSPORT-EDGE closure-lift (Gröbner / SOS), both arms kernel-verified, warm ===\n", flush=True)
    print("NOTE: `polyrith` (the historical Gröbner competitor) is DECOMMISSIONED in current Mathlib (its\n"
          "external Sage service is dead) ⇒ NOT a competitor. Baseline = full local native + subst_vars.\n")
    rows = []
    b_closed = t_closed = 0
    # --- Gröbner ---
    for name, vardecl, hyps, concl, ctrl in GROEBNER:
        base = _native_closes(vardecl, hyps, concl, name + "_b")
        cert = groebner_certificate(hyps, concl)
        treat = False
        if cert:
            hyp_decl = "".join(f" (h{i} : {h})" for i, h in enumerate(hyps))
            src = f"import Mathlib\n\ntheorem {name}_t ({vardecl}){hyp_decl} : {concl} := by\n  {cert['linear_combination']}\n"
            treat = _kv(src)
        b_closed += int(base); t_closed += int(treat)
        rows.append((name, "Gröbner", ctrl, base, treat))
        print(f"  {name:18s} [{'control' if ctrl else 'discrim'}]  native={base}  transport={treat}"
              f"{'  <<< LIFT' if (treat and not base) else ('  (cert:None)' if not cert else '')}", flush=True)
    # --- SOS ---
    for name, var, poly, ctrl in SOS:
        base = _native_closes(f"{var} : ℝ", [], f"{poly} ≥ 0", name + "_b")
        cert = sos_certificate(poly, var=var)
        treat = False
        if cert and cert.get("nlinarith_hints"):
            hints = ", ".join(cert["nlinarith_hints"])
            src = f"import Mathlib\n\ntheorem {name}_t ({var} : ℝ) : {poly} ≥ 0 := by\n  nlinarith [{hints}]\n"
            treat = _kv(src)
        b_closed += int(base); t_closed += int(treat)
        rows.append((name, "SOS", ctrl, base, treat))
        print(f"  {name:18s} [{'control' if ctrl else 'discrim'}]  native={base}  transport={treat}"
              f"{'  <<< LIFT' if (treat and not base) else ('  (cert:None)' if not cert else '')}", flush=True)

    n = len(rows)
    discrim = [r for r in rows if not r[2]]
    d_lift = sum(1 for _, _, _, base, treat in discrim if treat and not base)
    print(f"\n=== RESULT ===")
    print(f"  baseline (local native) closed: {b_closed}/{n}")
    print(f"  transport closed:               {t_closed}/{n}")
    print(f"  CLOSURE-LIFT (transport − native): {t_closed - b_closed:+d}/{n}  "
          f"(on discriminating rows: {d_lift}/{len(discrim)})")
    print("  → " + ("MEASURED LIFT: the transport edge kernel-closed goals the local native cascade could not."
                     if d_lift > 0 else
                     "NULL vs local native (transport edges subsumed here, OR baseline already closes them)."))
    print("  note: polyrith (the historical Gröbner competitor) is DECOMMISSIONED ⇒ the transport edge fills"
          " that gap locally + deterministically with an auditable cert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
